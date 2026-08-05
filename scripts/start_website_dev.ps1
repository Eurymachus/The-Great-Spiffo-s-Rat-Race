param(
    [int]$Port = 8001,
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

$env:DJANGO_ALLOWED_HOSTS = "localhost,127.0.0.1,[::1],192.168.4.100"

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
            -ArgumentList @("manage.py", "runserver", "0.0.0.0:$Port", "--noreload") `
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
    Write-Output "LAN website: http://192.168.4.100:$Port/"
    return
}

& $pythonPath $managePath runserver "0.0.0.0:$Port" --noreload
