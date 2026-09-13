param(
    [ValidateSet('Preflight','DryRun','Provision')][string]$Mode = 'Preflight',
    [Parameter(Mandatory=$true)][ValidatePattern('^[0-9a-f]{40}$')][string]$CurrentCommit,
    [Parameter(Mandatory=$true)][string]$CurrentReleaseRelative,
    [Parameter(Mandatory=$true)][string]$ReviewedCheckout,
    [PSCredential]$StagingCredential
)
$ErrorActionPreference = 'Stop'
$source = 'G:\RatRace_Staging'
$destination = 'G:\RatRace_StagingSecured'
$backup = 'G:\RatRace_StagingBackup'
. (Join-Path $PSScriptRoot 'Test-RatRaceLegacyRelease.ps1')

function Assert-Tree([string]$Path) {
    $cursor = [IO.DirectoryInfo]$Path
    while ($cursor) {
        if ($cursor.Exists -and ($cursor.Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw 'Reparse point in staging ancestry.' }
        $cursor = $cursor.Parent
    }
    foreach ($item in Get-ChildItem -LiteralPath $Path -Force -Recurse) {
        if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Reparse point in staging inventory.' }
    }
}
function Get-Inventory([string]$Path) {
    @(Get-ChildItem -LiteralPath $Path -File -Force -Recurse | ForEach-Object {
        [PSCustomObject]@{path=$_.FullName.Substring($Path.Length + 1); length=$_.Length; hash=(Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash}
    } | Sort-Object path)
}
function Set-ProtectedDirectory([string]$Path, [string]$RuntimeSid, [string]$Rights) {
    $acl = New-Object Security.AccessControl.DirectorySecurity
    $acl.SetAccessRuleProtection($true,$false)
    $acl.SetOwner((New-Object Security.Principal.SecurityIdentifier('S-1-5-32-544')))
    $entries = @(@('S-1-5-18','FullControl'), @('S-1-5-32-544','FullControl'))
    if ($RuntimeSid) { $entries += ,@($RuntimeSid,$Rights) }
    foreach ($entry in $entries) {
        $acl.AddAccessRule((New-Object Security.AccessControl.FileSystemAccessRule((New-Object Security.Principal.SecurityIdentifier($entry[0])), $entry[1], 'ContainerInherit,ObjectInherit','None','Allow')))
    }
    Set-Acl -LiteralPath $Path -AclObject $acl
}
if (-not (Test-Path -LiteralPath $source -PathType Container)) { throw 'Existing staging root missing.' }
if ((Test-Path -LiteralPath $destination) -or (Test-Path -LiteralPath $backup)) { throw 'Destination and backup must be absent. Never overwrite a prior migration.' }
if ([IO.Path]::IsPathRooted($CurrentReleaseRelative) -or $CurrentReleaseRelative -match '(^|[\\/])\.\.([\\/]|$)|:') { throw 'Current release must be a relative staging path.' }
$current = [IO.Path]::GetFullPath((Join-Path $source $CurrentReleaseRelative))
if (-not $current.StartsWith($source + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Current release outside staging.' }
Assert-Tree $source
foreach ($required in @('config\staging.env','venv\Scripts\python.exe')) {
    if (-not (Test-Path -LiteralPath (Join-Path $source $required) -PathType Leaf)) { throw "Missing required staging component: $required" }
}
if (-not (Test-Path -LiteralPath "$current\apps\website\manage.py")) { throw 'Current release structure missing.' }
$verifiedManifest = Test-RatRaceLegacyRelease -Release $current -Commit $CurrentCommit -ReviewedCheckout $ReviewedCheckout
$envText = [IO.File]::ReadAllText("$source\config\staging.env")
if ($envText -notmatch '(?m)^POSTGRES_PORT\s*=\s*["'']?5433["'']?\s*$') { throw 'Staging database must use port 5433.' }
foreach ($key in @('MEDIA_ROOT','AVATAR_QUARANTINE_ROOT','PZ_REFERENCE_ROOT')) {
    $match = [regex]::Match($envText, ('(?m)^' + $key + '\s*=\s*(.+)$'))
    $value = $match.Groups[1].Value.Trim().Trim('"',"'")
    if (-not $value -or $value -match '(^|[\\/])\.\.([\\/]|$)' -or -not [IO.Path]::GetFullPath($value).StartsWith($source + '\', [StringComparison]::OrdinalIgnoreCase) -or -not (Test-Path -LiteralPath $value)) { throw "Missing or out-of-scope persistent storage: $key" }
}
$clusters = @(Get-ChildItem -LiteralPath $source -Filter PG_VERSION -File -Recurse)
if ($clusters.Count -ne 1) { throw 'Exactly one staging PostgreSQL cluster must be inside the source root.' }
$cluster = $clusters[0].DirectoryName
# A stopped physical copy is required, including WAL and all tablespaces.
if (Test-Path -LiteralPath "$cluster\postmaster.pid") { throw 'PostgreSQL must be cleanly stopped before migration preflight. Never remove postmaster.pid to bypass this check.' }
$running = @(Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and $_.CommandLine.IndexOf($source + '\', [StringComparison]::OrdinalIgnoreCase) -ge 0 })
if ($running.Count -or @(Get-NetTCPConnection -LocalPort 5433,8002 -State Listen -ErrorAction SilentlyContinue).Count) { throw 'Stop only the existing staging web, worker and PostgreSQL before obtaining the offline migration inventory.' }
$inventory = Get-Inventory $source
$report = [PSCustomObject]@{mode=$Mode; source=$source; destination=$destination; backup=$backup; files=$inventory.Count; bytes=($inventory | Measure-Object length -Sum).Sum; currentCommit=$CurrentCommit; currentRelease=$CurrentReleaseRelative; cluster=$cluster.Substring($source.Length+1); sourceRetained=$true}
$report | ConvertTo-Json
if ($Mode -ne 'Provision') { return }
$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Provision requires one-time administrator elevation.' }
# A protected child can still be replaced by a principal controlling its parent.
foreach ($target in @($destination,$backup)) {
    $parent = ([IO.DirectoryInfo]$target).Parent
    while ($parent) {
        $acl = Get-Acl -LiteralPath $parent.FullName
        if ($acl.GetOwner([Security.Principal.SecurityIdentifier]).Value -notin @('S-1-5-18','S-1-5-32-544')) { throw 'Secure destination/backup ancestors under Administrators or SYSTEM ownership before provisioning.' }
        foreach ($rule in $acl.Access) {
            $sid = $rule.IdentityReference.Translate([Security.Principal.SecurityIdentifier]).Value
            if ($rule.AccessControlType -eq 'Allow' -and $sid -notin @('S-1-5-18','S-1-5-32-544') -and ($rule.FileSystemRights -band [Security.AccessControl.FileSystemRights]'Delete,DeleteSubdirectoriesAndFiles,ChangePermissions,TakeOwnership')) { throw 'An untrusted principal can replace a staging ancestor. Repair that boundary separately first.' }
        }
        $parent = $parent.Parent
    }
}
if (-not $StagingCredential -or $StagingCredential.UserName -notin @("$env:COMPUTERNAME\RatRaceStage",'.\RatRaceStage')) { throw 'Supply the dedicated local RatRaceStage credential.' }
$user = Get-LocalUser -Name RatRaceStage -ErrorAction SilentlyContinue
if (-not $user) { $user = New-LocalUser -Name RatRaceStage -Password $StagingCredential.Password -Description 'Limited staging runtime and deployment account' }
if ((Get-LocalGroupMember -SID 'S-1-5-32-544').SID.Value -contains $user.SID.Value -or -not $user.Enabled) { throw 'RatRaceStage must be enabled and non-administrator.' }
foreach ($target in @($backup,$destination)) {
    New-Item -ItemType Directory -Path $target | Out-Null
    Set-ProtectedDirectory $target '' 'ReadAndExecute'
    & robocopy.exe $source $target /E /COPY:DAT /DCOPY:DAT /XJ /R:0 /W:0 /NFL /NDL /NJH /NJS | Out-Null
    if ($LASTEXITCODE -ge 8) { throw 'Staging copy failed. Source is unchanged; retain destination for diagnosis.' }
    $copied = Get-Inventory $target
    if (($inventory | ConvertTo-Json -Depth 4 -Compress) -cne ($copied | ConvertTo-Json -Depth 4 -Compress)) { throw 'Backup/copy hash validation failed.' }
}
if (($inventory | ConvertTo-Json -Depth 4 -Compress) -cne ((Get-Inventory $source) | ConvertTo-Json -Depth 4 -Compress)) { throw 'Source changed while copying; do not cut over.' }
$destinationRelease = Join-Path $destination $CurrentReleaseRelative
[IO.File]::WriteAllText((Join-Path $destinationRelease 'staging-release.json'), ($verifiedManifest | ConvertTo-Json -Depth 5))
# Protected source backup remains byte-for-byte original, including environment/venv/cluster.
$report | ConvertTo-Json | Set-Content -LiteralPath "$backup\migration-report.json"
$inventory | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath "$backup\migration-inventory.json"
@(Get-CimInstance Win32_Service | Where-Object { $_.PathName -and $_.PathName.IndexOf($source + '\', [StringComparison]::OrdinalIgnoreCase) -ge 0 } | Select-Object Name,PathName,StartName,StartMode,State) | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath "$backup\staging-services.json"
foreach ($taskName in @('RatRaceStagingWeb','RatRaceStagingWorker')) {
    Export-ScheduledTask -TaskName $taskName -TaskPath '\' | Set-Content -LiteralPath "$backup\$taskName.xml"
}
Set-ProtectedDirectory $destination $user.SID.Value 'ReadAndExecute'
Set-ProtectedDirectory ($cluster.Replace($source + '\', $destination + '\')) '' 'ReadAndExecute'
foreach ($directory in @('releases','state','logs','runtime','repository.git')) {
    $path = Join-Path $destination $directory
    New-Item -ItemType Directory -Path $path -Force | Out-Null
    Set-ProtectedDirectory $path $user.SID.Value 'Modify'
}
# Rewrite only exact staging-root prefixes in the destination env, never the backup.
[IO.File]::WriteAllText("$destination\config\staging.env", $envText.Replace($source + '\', $destination + '\'))
foreach ($key in @('MEDIA_ROOT','AVATAR_QUARANTINE_ROOT','PZ_REFERENCE_ROOT')) {
    $value = [regex]::Match($envText, ('(?m)^' + $key + '\s*=\s*(.+)$')).Groups[1].Value.Trim().Trim('"',"'")
    Set-ProtectedDirectory ($value.Replace($source + '\', $destination + '\')) $user.SID.Value 'Modify'
}
Write-Output 'Offline copy verified. No copied executable was run. No tasks/services installed or started. Validate venv under the Limited deployment task, review PostgreSQL paths/ACLs and complete documented acceptance before retiring the old root.'
