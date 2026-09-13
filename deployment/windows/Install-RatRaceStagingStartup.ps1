param([Parameter(Mandatory=$true)][PSCredential]$StagingCredential)
$ErrorActionPreference = 'Stop'
$root = 'G:\RatRace\_Staging'
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'One-time installation/repair requires an administrator.' }
# Local accounts only: no domain nesting or SYSTEM identity can cross this boundary.
$name = $StagingCredential.UserName
if ($name -notmatch ('^(?:' + [regex]::Escape($env:COMPUTERNAME) + '|\.)\\([^\\]+)$')) { throw 'Supply a dedicated local account as COMPUTER\username.' }
$user = Get-LocalUser -Name $Matches[1]
$admins = @(Get-LocalGroupMember -SID 'S-1-5-32-544')
if ($admins.SID.Value -contains $user.SID.Value -or -not $user.Enabled) { throw 'Staging account must be enabled and must not belong to Administrators.' }
foreach ($path in @($root, "$root\launchers", "$root\state", "$root\logs")) {
    $cursor = [IO.DirectoryInfo]$path
    while ($cursor) {
        if ($cursor.Exists -and ($cursor.Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw 'Staging paths must not contain reparse points.' }
        $cursor = $cursor.Parent
    }
}
$launchers = Join-Path $root 'launchers'
function Set-ScopedAcl([string]$Path, [string]$Rights) {
    $acl = New-Object Security.AccessControl.DirectorySecurity
    $acl.SetAccessRuleProtection($true, $false)
    foreach ($entry in @(@('S-1-5-18','FullControl'), @('S-1-5-32-544','FullControl'), @($user.SID.Value,$Rights))) {
        $sid = New-Object Security.Principal.SecurityIdentifier($entry[0])
        $rule = New-Object Security.AccessControl.FileSystemAccessRule($sid, $entry[1], 'ContainerInherit,ObjectInherit', 'None', 'Allow')
        $acl.AddAccessRule($rule)
    }
    $acl.SetOwner((New-Object Security.Principal.SecurityIdentifier('S-1-5-32-544')))
    Set-Acl -LiteralPath $Path -AclObject $acl
}
New-Item -ItemType Directory -Path $root -Force | Out-Null
$rootAcl = Get-Acl -LiteralPath $root
$ownerSid = $rootAcl.GetOwner([Security.Principal.SecurityIdentifier]).Value
if ($ownerSid -notin @('S-1-5-18','S-1-5-32-544')) { throw 'Staging root must be owned by Administrators or SYSTEM.' }
$writeMask = [Security.AccessControl.FileSystemRights]'Write,Delete,DeleteSubdirectoriesAndFiles,ChangePermissions,TakeOwnership'
foreach ($rule in $rootAcl.Access) {
    $sid = $rule.IdentityReference.Translate([Security.Principal.SecurityIdentifier]).Value
    if ($rule.AccessControlType -eq 'Allow' -and ($rule.FileSystemRights -band $writeMask) -and $sid -notin @('S-1-5-18','S-1-5-32-544')) {
        throw 'Protect the staging root against non-administrator writes first. Preserve explicit PostgreSQL/storage subtree ACLs; this installer will not change them.'
    }
}
New-Item -ItemType Directory -Path $launchers -Force | Out-Null
Set-ScopedAcl $launchers 'ReadAndExecute'
foreach ($file in @('staging_release.py','Start-RatRaceStagingProcess.ps1','Switch-RatRaceStagingRelease.ps1','Staging-TaskControl.ps1','RatRaceProcessHelpers.ps1')) {
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot $file) -Destination (Join-Path $launchers $file) -Force
    # Remove any explicit ACL left by a previous installation.
    & icacls.exe (Join-Path $launchers $file) /reset | Out-Null
    if ($LASTEXITCODE) { throw 'Unable to protect permanent launcher file.' }
}
foreach ($directory in @('state','logs')) {
    $path = Join-Path $root $directory
    New-Item -ItemType Directory -Path $path -Force | Out-Null
    Set-ScopedAcl $path 'Modify'
}
# Stop and snapshot old staging-only trees before replacing their task actions.
. (Join-Path $PSScriptRoot 'RatRaceProcessHelpers.ps1')
$snapshot = @(Get-CimInstance Win32_Process)
$oldRoots = @(Get-RatRaceDeploymentProcessRoots -Processes $snapshot -InstallationRoot $root -PythonExecutable "$root\venv\Scripts\python.exe")
$oldRoots += @($snapshot | Where-Object { $_.CommandLine -and $_.CommandLine.Contains("$root\launchers\Start-RatRaceStagingProcess.ps1") })
$rootIds = @($oldRoots | Where-Object { $_.ProcessId -gt 0 } | Select-Object -ExpandProperty ProcessId)
$ids = @(Get-RatRaceProcessTreeIds -Processes $snapshot -RootProcessIds $rootIds)
foreach ($taskName in @('RatRaceStagingWeb','RatRaceStagingWorker')) {
    if (Get-ScheduledTask -TaskName $taskName -TaskPath '\' -ErrorAction SilentlyContinue) { Stop-ScheduledTask -TaskName $taskName -TaskPath '\' }
}
foreach ($processId in $ids) {
    $old = $snapshot | Where-Object ProcessId -eq $processId | Select-Object -First 1
    $now = Get-CimInstance Win32_Process -Filter "ProcessId=$processId"
    if ($now -and $now.CreationDate -eq $old.CreationDate) { Stop-Process -Id $processId -Force }
}
$service = New-Object -ComObject 'Schedule.Service'
$service.Connect()
foreach ($role in @('Web','Worker')) {
    $taskName = "RatRaceStaging$role"
    $launcher = Join-Path $launchers 'Start-RatRaceStagingProcess.ps1'
    $action = New-ScheduledTaskAction -Execute "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -Argument "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File `"$launcher`" -Process $role"
    $trigger = New-ScheduledTaskTrigger -AtStartup
    $trigger.Delay = 'PT30S'
    $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew
    Register-ScheduledTask -TaskName $taskName -TaskPath '\' -Action $action -Trigger $trigger -Settings $settings -User $name -Password ($StagingCredential.GetNetworkCredential().Password) -RunLevel Limited -Force | Out-Null
    $task = $service.GetFolder('\').GetTask($taskName)
    # Only task read/execute (run/stop), never write/delete/owner/DACL access.
    $task.SetSecurityDescriptor("O:BAG:BAD:P(A;;GA;;;SY)(A;;GA;;;BA)(A;;GRGX;;;$($user.SID.Value))", 0)
}
Write-Output 'Permanent staging tasks installed, not started. Run the staging switch as the dedicated account. PostgreSQL, production and GSA were not modified.'
