param([ValidateSet('Capture', 'Check')][string]$Mode = 'Check')
$ErrorActionPreference = 'Stop'
# Deliberately fixed staging scope. No live paths or retention apply option.
$root = 'G:\RatRace_Staging'
$python = Join-Path $root 'venv\Scripts\python.exe'
$stateRoot = Join-Path $root 'backup-operations'
$statusPath = Join-Path $stateRoot 'capture-status.json'
$checkPath = Join-Path $stateRoot 'check-status.json'
$tool = Join-Path $PSScriptRoot '..\..\scripts\staging_backup.py'
. (Join-Path $PSScriptRoot 'RatRaceProcessHelpers.ps1')
$names = @('RatRaceStagingWeb', 'RatRaceStagingWorker')
$eventSource = 'RatRaceStagingBackup'
$mutex = New-Object Threading.Mutex($false, 'Global\RatRaceStagingBackup')
$locked = $false
$paused = @()
$failed = $false
$stage = 'initialization'
$failureStage = ''
$failureLine = 0
function Save-State($path, $state, $detail) {
    $record = @{state=$state; checked_at=[DateTime]::UtcNow.ToString('o'); detail=$detail;
        stage=$stage; failure_stage=$failureStage; failure_line=$failureLine}
    $record | ConvertTo-Json | Set-Content -LiteralPath "$path.tmp" -Encoding UTF8
    Move-Item -LiteralPath "$path.tmp" -Destination $path -Force
}
function Run-Check($command) {
    $script:stage = "python-$command"
    & $python $tool $command --root $root
    if ($LASTEXITCODE -ne 0) { throw "Staging backup $command failed; inspect protected artifacts." }
}
try {
    $locked = $mutex.WaitOne(0)
    if (-not $locked) { throw 'Another backup operation is active.' }
    if (-not (Test-Path -LiteralPath $stateRoot -PathType Container)) { throw 'Protected state directory missing.' }
    if ($Mode -eq 'Check') {
        Run-Check 'check'
        $status = Get-Content -LiteralPath $statusPath -Raw | ConvertFrom-Json
        if ($status.state -ne 'success' -or [DateTime]::Parse($status.checked_at).ToUniversalTime() -lt [DateTime]::UtcNow.AddHours(-30)) {
            throw 'Latest backup run failed, was interrupted, or is stale.'
        }
        foreach ($name in @($names) + @('RatRaceStagingBackup')) {
            if (-not (Get-ScheduledTask -TaskName $name).Settings.Enabled) { throw 'A staging task is disabled.' }
        }
        if ((Get-ScheduledTaskInfo -TaskName 'RatRaceStagingBackup').LastTaskResult -ne 0) {
            throw 'Task Scheduler reports an unsuccessful backup run.'
        }
        Save-State $checkPath 'success' 'Complete backup integrity and freshness verified.'
    } else {
        Save-State $statusPath 'running' 'Capture starting.'
        Run-Check 'preflight'
        if ((Get-Volume -DriveLetter G).SizeRemaining -lt 2GB) { throw 'Insufficient backup disk space.' }
        $releaseLine = @(Get-Content -LiteralPath (Join-Path $root 'config\staging.env') | Where-Object { $_ -match '^RELEASE_ID=' })
        $stage = 'validate-task-release'
        if ($releaseLine.Count -ne 1) { throw 'Release identity missing or ambiguous.' }
        $release = ($releaseLine[0] -split '=', 2)[1].Trim().Trim('"').Trim("'")
        if ($release -notmatch '^[a-f0-9]{7,40}$') { throw 'Invalid release identity.' }
        $releasePath = Join-Path $root "releases\$release"
        foreach ($name in $names) {
            $task = Get-ScheduledTask -TaskName $name
            if (-not $task.Settings.Enabled -or $task.State -ne 'Running' -or
                $task.Actions.Count -ne 1 -or $task.Actions[0].Arguments -notlike "*$releasePath*") {
                throw 'Staging task is not running the expected release.'
            }
        }
        # Operator deployments must not overlap this window. Disable triggers before stopping.
        $stage = 'disable-staging-triggers'
        foreach ($name in $names) {
            $paused += $name
            Disable-ScheduledTask -TaskName $name | Out-Null
        }
        $stage = 'cooperative-staging-stop'
        & (Join-Path $PSScriptRoot 'Stop-RatRaceStagingProcesses.ps1')
        $stage = 'verify-staging-stopped'
        Assert-RatRaceDeploymentStopped -Processes @(Get-CimInstance Win32_Process) -InstallationRoot $root -PythonExecutable $python
        if (Get-NetTCPConnection -LocalPort 8002 -State Listen -ErrorAction SilentlyContinue) { throw 'Staging web listener remains.' }
        Run-Check 'capture'
        Run-Check 'check'
    }
} catch {
    $failed = $true
    $failureStage = $stage
    $failureLine = $_.InvocationInfo.ScriptLineNumber
    # Avoid writing exception/child details that might contain protected information.
    if ($locked -and (Test-Path -LiteralPath $stateRoot)) {
        if ($Mode -eq 'Capture') { Save-State $statusPath 'failed' 'Capture or verification failed; review retained artifacts and task history.' }
        else { Save-State $checkPath 'failed' 'Backup failed, stale, missing, corrupt, or staging task disabled.' }
    }
} finally {
    foreach ($name in $paused) {
        try {
            Enable-ScheduledTask -TaskName $name | Out-Null
            Start-ScheduledTask -TaskName $name
        } catch { $failed = $true; $failureStage = 'restart-staging-task'; $failureLine=$_.InvocationInfo.ScriptLineNumber }
    }
    if ($paused.Count) {
        $ready = $false
        for ($attempt=0; $attempt -lt 45; $attempt++) {
            Start-Sleep -Seconds 2
            try {
                $health = Invoke-RestMethod 'http://127.0.0.1:8002/health/ready/' -Headers @{'X-Forwarded-Proto'='https'} -TimeoutSec 3
                $processes = @(Get-CimInstance Win32_Process)
                $web = @(Get-RatRaceDeploymentProcessRoots -Processes $processes -InstallationRoot $root -PythonExecutable $python -Process Web)
                $worker = @(Get-RatRaceDeploymentProcessRoots -Processes $processes -InstallationRoot $root -PythonExecutable $python -Process Worker)
                if ($health.release -eq $release -and $web.Count -eq 1 -and $worker.Count -eq 1) { $ready=$true; break }
            } catch { }
        }
        if (-not $ready) { $failed=$true; $failureStage='staging-readiness' }
    }
    if ($locked -and $Mode -eq 'Capture' -and (Test-Path -LiteralPath $stateRoot)) {
        if ($failed) { Save-State $statusPath 'failed' 'Backup or staging recovery failed; operator review required.' }
        else { Save-State $statusPath 'success' 'Backup verified; staging web and worker readiness restored.' }
    }
    if ($locked) { $mutex.ReleaseMutex() }
    $mutex.Dispose()
}
if ($failed) {
    Write-EventLog -LogName Application -Source $eventSource -EntryType Error -EventId 4101 -Message "Staging backup $Mode failed. Review $stateRoot and Task Scheduler."
    exit 1
}
Write-EventLog -LogName Application -Source $eventSource -EntryType Information -EventId 4100 -Message "Staging backup $Mode passed. Status: $stateRoot"
exit 0
