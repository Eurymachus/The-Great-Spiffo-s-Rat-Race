param([Parameter(Mandatory=$true)][ValidateSet('Validate','Stop','Start','Verify')][string]$Operation)
$ErrorActionPreference = 'Stop'
$root = 'G:\RatRace_StagingSecured'
$python = Join-Path $root 'venv\Scripts\python.exe'
$launcher = Join-Path $root 'launchers\Start-RatRaceStagingProcess.ps1'
$engine = Join-Path $root 'launchers\staging_release.py'
. (Join-Path $PSScriptRoot 'RatRaceProcessHelpers.ps1')
$names = @('RatRaceStagingWeb', 'RatRaceStagingWorker')

function Get-StagingRoots($snapshot) {
    $legacy = @(Get-RatRaceDeploymentProcessRoots -Processes $snapshot -InstallationRoot $root -PythonExecutable $python)
    $fixed = @($snapshot | Where-Object {
        $_.CommandLine -and ($_.CommandLine.Contains($launcher) -or
            ($_.CommandLine.Contains($engine) -and $_.CommandLine -match 'run\s+--role\s+(Web|Worker)(?:\s|$)'))
    })
    @(@($legacy) + @($fixed) | Sort-Object ProcessId -Unique)
}

try {
    foreach ($role in @('Web','Worker')) {
        $task = Get-ScheduledTask -TaskName "RatRaceStaging$role" -TaskPath '\'
        $expected = "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File `"$launcher`" -Process $role"
        if (@($task.Actions).Count -ne 1 -or $task.Actions[0].Arguments -cne $expected -or
            $task.Actions[0].Execute -ine "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -or
            $task.Principal.RunLevel -ne 'Limited' -or $task.Principal.UserId -match '^(SYSTEM|S-1-5-18|S-1-5-19|S-1-5-20)$') {
            throw "Permanent staging task $role needs administrator repair."
        }
        if ($role -eq 'Web') { $account = $task.Principal.UserId }
        elseif ($account -ne $task.Principal.UserId) { throw 'Staging tasks must share the staging account.' }
    }
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $accountSid = if ($account -match '^S-1-') { $account } else { (New-Object Security.Principal.NTAccount($account)).Translate([Security.Principal.SecurityIdentifier]).Value }
    if ($accountSid -ne $identity.User.Value) { throw 'Run the switch as the installed staging account, not another operator or administrator.' }
    if ($Operation -eq 'Validate') { '{"valid":true}'; exit 0 }

    if ($Operation -eq 'Stop') {
        # Snapshot descendants BEFORE Task Scheduler can detach surviving children.
        $snapshot = @(Get-CimInstance Win32_Process)
        $roots = @(Get-StagingRoots $snapshot)
        $rootIds = @($roots | Where-Object { $_.ProcessId -gt 0 } | Select-Object -ExpandProperty ProcessId)
        $ids = @(Get-RatRaceProcessTreeIds -Processes $snapshot -RootProcessIds $rootIds)
        foreach ($name in $names) { Stop-ScheduledTask -TaskName $name -TaskPath '\' }
        foreach ($processId in $ids) {
            $old = $snapshot | Where-Object ProcessId -eq $processId | Select-Object -First 1
            $now = Get-CimInstance Win32_Process -Filter "ProcessId=$processId"
            if ($now -and $now.CreationDate -eq $old.CreationDate) { Stop-Process -Id $processId -Force }
        }
        $deadline = [DateTime]::UtcNow.AddSeconds(30)
        do {
            $remaining = @(Get-StagingRoots @(Get-CimInstance Win32_Process))
            $running = @($names | Where-Object { (Get-ScheduledTask -TaskName $_ -TaskPath '\').State -eq 'Running' })
            if (-not $remaining.Count -and -not $running.Count) { break }
            Start-Sleep -Milliseconds 250
        } while ([DateTime]::UtcNow -lt $deadline)
        if ($remaining.Count -or $running.Count) { throw 'Complete staging process-tree cleanup could not be proved.' }
        '{"stopped":true}'; exit 0
    }
    if ($Operation -eq 'Start') {
        foreach ($name in $names) { Start-ScheduledTask -TaskName $name -TaskPath '\' }
        '{"started":true}'; exit 0
    }
    $snapshot = @(Get-CimInstance Win32_Process)
    $legacy = @(Get-RatRaceDeploymentProcessRoots -Processes $snapshot -InstallationRoot $root -PythonExecutable $python)
    if ($legacy.Count) { throw 'Unexpected legacy staging web/worker processes remain.' }
    $result = @{}
    foreach ($role in @('Web','Worker')) {
        if ((Get-ScheduledTask -TaskName "RatRaceStaging$role" -TaskPath '\').State -ne 'Running') { throw "$role task is not running" }
        $runtimes = @($snapshot | Where-Object { $_.CommandLine -and $_.CommandLine.Contains($engine) -and $_.CommandLine -match "run\s+--role\s+$role(?:\s|$)" -and $_.Name -match '^python(w)?\.exe$' })
        # venv redirector and its interpreter are one logical process tree.
        $leaves = @($runtimes | Where-Object { $runtimes.ParentProcessId -notcontains $_.ProcessId })
        if ($leaves.Count -ne 1) { throw "Expected exactly one staging $role runtime; found $($leaves.Count)." }
        $result[$role.ToLowerInvariant() + '_pid'] = [int]$leaves[0].ProcessId
    }
    $listeners = @(Get-NetTCPConnection -State Listen -LocalPort 8002 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique)
    if ($listeners.Count -ne 1 -or $listeners[0] -ne $result.web_pid) { throw 'Port 8002 is not exclusively owned by the staging web runtime.' }
    $result | ConvertTo-Json -Compress
} catch {
    Write-Error ("Staging task operation failed. If access is denied, ask the administrator to grant only read/run/stop on RatRaceStagingWeb and RatRaceStagingWorker to the staging account. No task definition changes are permitted. " + $_.Exception.Message)
    exit 1
}
