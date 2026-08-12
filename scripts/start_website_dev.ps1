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

function Get-ReferenceWorkerProcesses {
    $escapedPythonPath = [Regex]::Escape($pythonPath)
    $candidates = @(
        Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
            Where-Object {
                $_.CommandLine -match $escapedPythonPath -and
                $_.CommandLine -match "manage\.py\s+run_reference_update_worker(?:\s|$)"
            }
    )
    $candidateIds = @($candidates.ProcessId)
    @($candidates | Where-Object { $_.ParentProcessId -notin $candidateIds })
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
} else {
    Write-Output "Reference worker already running with PID $($workerProcesses[0].ProcessId)."
}

Set-Location -LiteralPath $workspacePath
if ($Background) {
    $listeners = @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
    if ($listeners.Count -gt 1) {
        throw "Multiple processes are listening on port $Port."
    }
    if ($listeners.Count -eq 0) {
        $webProcess = Start-Process `
            -FilePath $pythonPath `
            -ArgumentList @("manage.py", "runserver", "${BindAddress}:$Port", "--noreload") `
            -WorkingDirectory $websitePath `
            -WindowStyle Hidden `
            -PassThru
        Write-Output "Website started with PID $($webProcess.Id)."
    } else {
        $listenerProcess = Get-CimInstance Win32_Process `
            -Filter "ProcessId = $($listeners[0].OwningProcess)" `
            -ErrorAction SilentlyContinue
        if (
            -not $listenerProcess -or
            $listenerProcess.CommandLine -notmatch [Regex]::Escape($pythonPath) -or
            $listenerProcess.CommandLine -notmatch "manage\.py\s+runserver"
        ) {
            throw "Port $Port is owned by a process outside this website launcher."
        }
        Write-Output "Website already running with PID $($listenerProcess.ProcessId)."
    }
    Write-Output "Local website: http://127.0.0.1:$Port/"
    if ($LanAddress) {
        Write-Output "LAN website: http://${LanAddress}:$Port/"
    }
    return
}

& $pythonPath $managePath runserver "${BindAddress}:$Port" --noreload
