param(
    [int]$Port = 8001,
    [string]$BindAddress = "127.0.0.1",
    [string]$LanAddress = "",
    [switch]$Background
)

$workspacePath = if ($PSScriptRoot) {
    Split-Path -Parent $PSScriptRoot
} else {
    (Get-Location).Path
}
$environmentPath = Join-Path $workspacePath ".env"
$pythonPath = Join-Path $workspacePath ".venv\Scripts\python.exe"
$websitePath = Join-Path $workspacePath "apps\website"
$managePath = Join-Path $websitePath "manage.py"
$workerOutputPath = Join-Path $workspacePath "worker.stdout.log"
$workerErrorPath = Join-Path $workspacePath "worker.stderr.log"
$websitePidPath = Join-Path $workspacePath ".website-dev.pid"
$websiteListenerPidPath = Join-Path $workspacePath ".website-dev.listener.pid"
$workerPidPath = Join-Path $workspacePath ".reference-worker.pid"

if (-not (Test-Path -LiteralPath $environmentPath)) {
    throw "The local .env file is required."
}

# Windows environment names are case-insensitive, but Start-Process can receive
# both PATH and Path from some parent applications and reject the duplicate key.
$processEnvironment = [Environment]::GetEnvironmentVariables("Process")
$pathKeys = @($processEnvironment.Keys | Where-Object { $_ -ieq "Path" })
if ($pathKeys.Count -gt 1) {
    $pathValue = [Environment]::GetEnvironmentVariable("Path", "Process")
    foreach ($pathKey in $pathKeys) {
        [Environment]::SetEnvironmentVariable([string]$pathKey, $null, "Process")
    }
    [Environment]::SetEnvironmentVariable("Path", $pathValue, "Process")
}

Get-Content -LiteralPath $environmentPath | ForEach-Object {
    $line = $_.Trim()
    if ($line -and -not $line.StartsWith("#") -and $line.Contains("=")) {
        $parts = $line.Split("=", 2)
        $name = $parts[0].Trim()
        $value = $parts[1].Trim()
        if (
            ($value.StartsWith('"') -and $value.EndsWith('"')) -or
            ($value.StartsWith("'") -and $value.EndsWith("'"))
        ) {
            $value = $value.Substring(1, $value.Length - 2)
        }
        [Environment]::SetEnvironmentVariable($name, $value, "Process")
    }
}

$allowedHosts = @("localhost", "127.0.0.1", "[::1]")
if ($LanAddress) {
    $allowedHosts += $LanAddress
}
$env:DJANGO_ALLOWED_HOSTS = $allowedHosts -join ","
$env:RAT_RACE_CANONICAL_DEV_LAUNCHER = "1"

function Get-ReferenceWorkerCandidates {
    @(
        Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
            Where-Object {
                $_.CommandLine -match "manage\.py\s+run_reference_update_worker(?:\s|$)"
            }
    )
}

function Get-ReferenceWorkerProcesses {
    $candidates = @(Get-ReferenceWorkerCandidates)
    $candidateIds = @($candidates.ProcessId)
    @($candidates | Where-Object { $_.ParentProcessId -notin $candidateIds })
}

function Get-WebsiteCandidates {
    $escapedEndpoint = [Regex]::Escape("${BindAddress}:$Port")
    @(
        Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
            Where-Object {
                $_.CommandLine -match "manage\.py\s+runserver\s+$escapedEndpoint\s+--noreload(?:\s|$)"
            }
    )
}

function Get-ListenerProcessIds {
    $endpointPattern = "^\s*TCP\s+\S+:$Port\s+\S+\s+LISTENING\s+(\d+)\s*$"
    @(
        & netstat.exe -ano -p tcp |
            ForEach-Object {
                if ($_ -match $endpointPattern) {
                    [int]$Matches[1]
                }
            } |
            Sort-Object -Unique
    )
}

function Stop-ProcessCandidates {
    param(
        [object[]]$Candidates,
        [string]$Label
    )

    foreach ($candidate in @($Candidates | Sort-Object ProcessId -Descending)) {
        Stop-Process -Id $candidate.ProcessId -Force -ErrorAction SilentlyContinue
        Write-Output "Stopped $Label PID $($candidate.ProcessId)."
    }
}

function Stop-RecordedProcessTree {
    param(
        [string]$PidPath,
        [string]$Label
    )

    if (-not (Test-Path -LiteralPath $PidPath)) {
        return
    }
    $recordedPid = 0
    if ([int]::TryParse((Get-Content -LiteralPath $PidPath -Raw).Trim(), [ref]$recordedPid)) {
        & taskkill.exe /PID $recordedPid /T /F 2>$null | Out-Null
        Stop-Process -Id $recordedPid -Force -ErrorAction SilentlyContinue
        Write-Output "Stopped recorded $Label process tree $recordedPid."
    }
    Remove-Item -LiteralPath $PidPath -Force -ErrorAction SilentlyContinue
}

if ($Background) {
    Stop-RecordedProcessTree -PidPath $websitePidPath -Label "website"
    Stop-RecordedProcessTree -PidPath $websiteListenerPidPath -Label "website listener"
    Stop-RecordedProcessTree -PidPath $workerPidPath -Label "reference worker"
    $listenerShutdownDeadline = (Get-Date).AddSeconds(5)
    do {
        Start-Sleep -Milliseconds 100
        $listenerIdsAfterRecordedStop = @(Get-ListenerProcessIds)
    } while (
        $listenerIdsAfterRecordedStop.Count -gt 0 -and
        (Get-Date) -lt $listenerShutdownDeadline
    )
    $websiteCandidates = @(Get-WebsiteCandidates)
    $websiteCandidateIds = @($websiteCandidates.ProcessId)
    $foreignListenerIds = @(Get-ListenerProcessIds | Where-Object { $_ -notin $websiteCandidateIds })
    if ($foreignListenerIds.Count -gt 0) {
        throw "Port $Port is owned by a process outside this website launcher: $($foreignListenerIds -join ', ')."
    }

    Stop-ProcessCandidates -Candidates $websiteCandidates -Label "website"
    Stop-ProcessCandidates -Candidates @(Get-ReferenceWorkerCandidates) -Label "reference worker"

    $shutdownDeadline = (Get-Date).AddSeconds(5)
    do {
        Start-Sleep -Milliseconds 100
        $remainingWebsites = @(Get-WebsiteCandidates)
        $remainingWorkers = @(Get-ReferenceWorkerCandidates)
    } while (
        ($remainingWebsites.Count -gt 0 -or $remainingWorkers.Count -gt 0) -and
        (Get-Date) -lt $shutdownDeadline
    )
    if ($remainingWebsites.Count -gt 0 -or $remainingWorkers.Count -gt 0) {
        throw "The previous local website process trees did not stop cleanly."
    }
    $remainingListenerIds = @(Get-ListenerProcessIds)
    if ($remainingListenerIds.Count -gt 0) {
        throw "Port $Port still has listener processes after shutdown: $($remainingListenerIds -join ', ')."
    }
}

$workerProcesses = @(Get-ReferenceWorkerProcesses)
if ($workerProcesses.Count -gt 1) {
    throw "Multiple reference workers are already running: $($workerProcesses.ProcessId -join ', ')."
}
if ($workerProcesses.Count -eq 0) {
    $workerProcess = Start-Process `
        -FilePath $pythonPath `
        -ArgumentList @("manage.py", "run_reference_update_worker") `
        -WorkingDirectory $websitePath `
        -WindowStyle Hidden `
        -RedirectStandardOutput $workerOutputPath `
        -RedirectStandardError $workerErrorPath `
        -PassThru
    Start-Sleep -Milliseconds 500
    if ($workerProcess.HasExited) {
        throw "The reference worker exited during startup. Check worker.stderr.log."
    }
    Write-Output "Reference worker started with PID $($workerProcess.Id)."
    Set-Content -LiteralPath $workerPidPath -Value $workerProcess.Id
} else {
    Write-Output "Reference worker already running with PID $($workerProcesses[0].ProcessId)."
}

Set-Location -LiteralPath $workspacePath
if ($Background) {
    $webProcess = Start-Process `
        -FilePath $pythonPath `
        -ArgumentList @("manage.py", "runserver", "${BindAddress}:$Port", "--noreload") `
        -WorkingDirectory $websitePath `
        -WindowStyle Hidden `
        -PassThru
    Write-Output "Website started with PID $($webProcess.Id)."
    Set-Content -LiteralPath $websitePidPath -Value $webProcess.Id

    $startupDeadline = (Get-Date).AddSeconds(20)
    $websiteReady = $false
    $listenerProcessIds = @()
    do {
        Start-Sleep -Milliseconds 250
        $listenerProcessIds = @(Get-ListenerProcessIds)
        try {
            $response = Invoke-WebRequest `
                -UseBasicParsing `
                -Uri "http://${BindAddress}:$Port/" `
                -TimeoutSec 2 `
                -ErrorAction Stop
            $websiteReady = (
                $response.StatusCode -ge 200 -and
                $response.StatusCode -lt 500 -and
                $listenerProcessIds.Count -eq 1
            )
        } catch {
            $websiteReady = $false
        }
    } while (-not $websiteReady -and (Get-Date) -lt $startupDeadline)
    if (-not $websiteReady) {
        throw "The website did not establish exactly one healthy listener on port $Port during startup. Listener PIDs: $($listenerProcessIds -join ', ')."
    }

    if ($webProcess.HasExited -or $workerProcess.HasExited) {
        throw "Expected one website and one reference worker process tree after startup."
    }
    Set-Content -LiteralPath $websiteListenerPidPath -Value $listenerProcessIds[0]
    Write-Output "Verified one website listener with PID $($listenerProcessIds[0])."
    Write-Output "Local website: http://127.0.0.1:$Port/"
    if ($LanAddress) {
        Write-Output "LAN website: http://${LanAddress}:$Port/"
    }
    return
}

& $pythonPath $managePath runserver "${BindAddress}:$Port" --noreload
