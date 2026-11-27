param([ValidateRange(5, 600)][int]$TimeoutSeconds = 120)
$ErrorActionPreference = 'Stop'
$root = 'G:\RatRace_Staging'
$controlRoot = Join-Path $root 'logs\process-control'
foreach ($path in @('G:\', $root, (Join-Path $root 'logs'), $controlRoot)) {
    if ((Get-Item -LiteralPath $path -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) {
        throw 'Redirected process-control path refused.'
    }
}
$targets = @()
foreach ($role in @('web', 'worker')) {
    $task = Get-ScheduledTask -TaskName "RatRaceStaging$role"
    if ($task.Settings.Enabled) { throw 'Disable staging launch triggers before requesting a stop.' }
    $descriptor = Join-Path $controlRoot "$role.json"
    if ((Get-Item -LiteralPath $descriptor -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Redirected descriptor refused.' }
    $record = Get-Content -LiteralPath $descriptor -Raw | ConvertFrom-Json
    if ($record.state -ne 'running' -or $record.token -notmatch '^[a-f0-9]{32}$' -or $record.pid -le 0) {
        throw 'Current logger descriptor missing or invalid.'
    }
    $process = Get-CimInstance Win32_Process -Filter "ProcessId=$($record.pid)"
    if (-not $process -or $process.CommandLine -notmatch [regex]::Escape($root + '\') -or
        $process.CommandLine -notmatch 'run_logged_process\.py' -or
        $process.CommandLine -notmatch "--label\s+$role(?:\s|$)" -or
        $process.CommandLine -notmatch [regex]::Escape($controlRoot) -or
        [Math]::Abs(($process.CreationDate.ToUniversalTime() - [DateTime]::Parse($record.started_at).ToUniversalTime()).TotalSeconds) -gt 30) {
        throw 'Logger process identity does not match its current descriptor.'
    }
    $request = Join-Path $controlRoot ($record.token + '.stop')
    if ((Test-Path -LiteralPath $request) -and ((Get-Item -LiteralPath $request -Force).Attributes -band [IO.FileAttributes]::ReparsePoint)) {
        throw 'Redirected request refused.'
    }
    $targets += [pscustomobject]@{Record=$record; Descriptor=$descriptor; Request=$request; Created=$process.CreationDate}
}
# Validate both current identities before sending either request. No process killing.
foreach ($target in $targets) { [IO.File]::WriteAllText($target.Request, $target.Record.token) }
$deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
do {
    $finished = $true
    foreach ($target in $targets) {
        $process = Get-CimInstance Win32_Process -Filter "ProcessId=$($target.Record.pid)"
        if ($process -and $process.CreationDate -eq $target.Created) { $finished=$false; continue }
        $receipt = Get-Content -LiteralPath $target.Descriptor -Raw | ConvertFrom-Json
        if ($receipt.token -ne $target.Record.token -or $receipt.state -ne 'exited' -or $receipt.exit_code -ne 0) {
            throw 'Logger exited without a successful drain/seal receipt.'
        }
    }
    if ($finished) { break }
    Start-Sleep -Milliseconds 500
} while ([DateTime]::UtcNow -lt $deadline)
if (-not $finished) { throw 'Cooperative staging shutdown timed out; no forced termination was attempted.' }
. (Join-Path $PSScriptRoot 'RatRaceProcessHelpers.ps1')
$deadline = [DateTime]::UtcNow.AddSeconds(10)
do {
    $roots = @(Get-RatRaceDeploymentProcessRoots -Processes @(Get-CimInstance Win32_Process) -InstallationRoot $root -PythonExecutable (Join-Path $root 'venv\Scripts\python.exe'))
    if (-not $roots.Count) { break }
    Start-Sleep -Milliseconds 500
} while ([DateTime]::UtcNow -lt $deadline)
if ($roots.Count) { throw 'A staging launcher or runtime remains after cooperative stop.' }
Write-Output 'Staging web and worker exited cleanly; their logger streams were drained and sealed.'
