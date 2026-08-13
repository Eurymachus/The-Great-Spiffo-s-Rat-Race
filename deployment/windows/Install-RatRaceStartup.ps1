param(
    [string]$ReleaseRoot = "G:\RatRace\releases\ed3fd6003c9d",
    [string]$EnvironmentFile = "G:\RatRace\config\acceptance.env",
    [string]$PythonExecutable = "G:\RatRace\venv\Scripts\python.exe",
    [string]$PostgresRoot = "G:\RatRace\postgres",
    [string]$LogRoot = "G:\RatRace\logs",
    [int]$WebPort = 8000
)

$ErrorActionPreference = "Stop"
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw "Run this script from an elevated PowerShell session."
}

$releasePath = (Resolve-Path -LiteralPath $ReleaseRoot).Path
$environmentPath = (Resolve-Path -LiteralPath $EnvironmentFile).Path
$pythonPath = (Resolve-Path -LiteralPath $PythonExecutable).Path
$postgresPath = (Resolve-Path -LiteralPath $PostgresRoot).Path
$scheduledLauncher = Join-Path $releasePath "deployment\windows\Start-RatRaceScheduledProcess.ps1"
$pgCtl = Join-Path $postgresPath "runtime\pgsql\bin\pg_ctl.exe"
$dataRoot = Join-Path $postgresPath "data"

foreach ($requiredPath in @($scheduledLauncher, $pgCtl, $dataRoot)) {
    if (-not (Test-Path -LiteralPath $requiredPath)) {
        throw "Required deployment path is missing: $requiredPath"
    }
}
New-Item -ItemType Directory -Path $LogRoot -Force | Out-Null

$postgresServiceName = "RatRacePostgres"
if (-not (Get-Service -Name $postgresServiceName -ErrorAction SilentlyContinue)) {
    & $pgCtl register `
        -D $dataRoot `
        -N $postgresServiceName `
        -S auto `
        -o "-h 127.0.0.1 -p 5432"
    if ($LASTEXITCODE) {
        throw "PostgreSQL service registration failed with exit code $LASTEXITCODE."
    }
}

function New-RatRaceStartupTask {
    param(
        [Parameter(Mandatory = $true)]
        [ValidateSet("Web", "Worker")]
        [string]$Process
    )

    $taskName = "RatRace$Process"
    $logFile = Join-Path $LogRoot ($Process.ToLowerInvariant() + ".log")
    $arguments = @(
        "-NoProfile",
        "-ExecutionPolicy Bypass",
        "-File `"$scheduledLauncher`"",
        "-Process $Process",
        "-ReleaseRoot `"$releasePath`"",
        "-EnvironmentFile `"$environmentPath`"",
        "-PythonExecutable `"$pythonPath`"",
        "-LogFile `"$logFile`"",
        "-Port $WebPort"
    ) -join " "
    $action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $arguments
    $trigger = New-ScheduledTaskTrigger -AtStartup
    $trigger.Delay = "PT30S"
    $settings = New-ScheduledTaskSettingsSet `
        -StartWhenAvailable `
        -RestartCount 999 `
        -RestartInterval (New-TimeSpan -Minutes 1) `
        -ExecutionTimeLimit ([TimeSpan]::Zero) `
        -MultipleInstances IgnoreNew
    $taskPrincipal = New-ScheduledTaskPrincipal `
        -UserId "SYSTEM" `
        -LogonType ServiceAccount `
        -RunLevel Highest
    Register-ScheduledTask `
        -TaskName $taskName `
        -Action $action `
        -Trigger $trigger `
        -Settings $settings `
        -Principal $taskPrincipal `
        -Description "The Great Spiffo's Rat Race $Process process." `
        -Force | Out-Null
}

New-RatRaceStartupTask -Process Web
New-RatRaceStartupTask -Process Worker

$postgresService = Get-Service -Name $postgresServiceName
if ($postgresService.Status -ne "Running") {
    & $pgCtl stop -D $dataRoot -m fast -w
    if ($LASTEXITCODE) {
        throw "Unable to stop the manually launched PostgreSQL process."
    }
    Start-Service -Name $postgresServiceName
    (Get-Service -Name $postgresServiceName).WaitForStatus(
        "Running", [TimeSpan]::FromSeconds(30)
    )
}
& sc.exe failure $postgresServiceName `
    reset= 3600 `
    actions= restart/5000/restart/10000/restart/30000 | Out-Null
if ($LASTEXITCODE) { throw "Unable to configure PostgreSQL recovery actions." }
& sc.exe failureflag $postgresServiceName 1 | Out-Null
if ($LASTEXITCODE) { throw "Unable to enable PostgreSQL recovery actions." }
& sc.exe config $postgresServiceName start= delayed-auto | Out-Null
if ($LASTEXITCODE) { throw "Unable to configure PostgreSQL delayed startup." }

$allProcesses = @(Get-CimInstance Win32_Process)
$manualRoots = @(
    $allProcesses |
        Where-Object {
            $_.Name -eq "powershell.exe" -and
            $_.CommandLine -match "Start-RatRaceProcess\.ps1" -and
            $_.CommandLine -match "-Process (Web|Worker)"
        } |
        Select-Object -ExpandProperty ProcessId
)
$processesToStop = New-Object System.Collections.Generic.HashSet[int]
function Add-ProcessTree {
    param([int]$ProcessId)
    foreach ($child in $allProcesses | Where-Object ParentProcessId -eq $ProcessId) {
        Add-ProcessTree -ProcessId ([int]$child.ProcessId)
    }
    [void]$processesToStop.Add($ProcessId)
}
foreach ($rootProcessId in $manualRoots) {
    Add-ProcessTree -ProcessId ([int]$rootProcessId)
}
foreach ($processId in @($processesToStop) | Sort-Object -Descending) {
    Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
}

Start-ScheduledTask -TaskName "RatRaceWeb"
Start-ScheduledTask -TaskName "RatRaceWorker"

$readinessStatus = "000"
for ($attempt = 0; $attempt -lt 30; $attempt++) {
    Start-Sleep -Seconds 2
    $readinessStatus = & curl.exe `
        -sS `
        -o NUL `
        -w "%{http_code}" `
        -H "X-Forwarded-Proto: https" `
        --max-time 10 `
        "http://127.0.0.1:$WebPort/health/ready/"
    if ($readinessStatus -eq "200") { break }
}
if ($readinessStatus -ne "200") {
    throw "Rat Race readiness did not recover after startup-task cutover."
}

$result = [pscustomobject]@{
    PostgreSQL = (Get-Service -Name $postgresServiceName).Status.ToString()
    WebTask = (Get-ScheduledTask -TaskName "RatRaceWeb").State.ToString()
    WorkerTask = (Get-ScheduledTask -TaskName "RatRaceWorker").State.ToString()
    Readiness = $readinessStatus
}
$result | ConvertTo-Json -Compress
