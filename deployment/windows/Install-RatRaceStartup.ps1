param(
    [string]$InstallationRoot = "G:\RatRace",
    [ValidatePattern('^[A-Za-z][A-Za-z0-9_-]*$')]
    [string]$DeploymentName = "RatRace",
    [string]$ReleaseRoot = "G:\RatRace\releases\ed3fd6003c9d",
    [string]$EnvironmentFile = "G:\RatRace\config\acceptance.env",
    [string]$PythonExecutable = "G:\RatRace\venv\Scripts\python.exe",
    [string]$PostgresRoot = "G:\RatRace\postgres",
    [string]$LogRoot = "G:\RatRace\logs",
    [int]$WebPort = 8000,
    [ValidateRange(1, 65535)]
    [int]$PostgresPort = 5432
)

$ErrorActionPreference = "Stop"
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw "Run this script from an elevated PowerShell session."
}

$releasePath = (Resolve-Path -LiteralPath $ReleaseRoot).Path
$installationPath = (Resolve-Path -LiteralPath $InstallationRoot).Path
$environmentPath = (Resolve-Path -LiteralPath $EnvironmentFile).Path
$pythonPath = (Resolve-Path -LiteralPath $PythonExecutable).Path
$postgresPath = (Resolve-Path -LiteralPath $PostgresRoot).Path
$scheduledLauncher = Join-Path $releasePath "deployment\windows\Start-RatRaceScheduledProcess.ps1"
$processHelpers = Join-Path $releasePath "deployment\windows\RatRaceProcessHelpers.ps1"
$pgCtl = Join-Path $postgresPath "runtime\pgsql\bin\pg_ctl.exe"
$dataRoot = Join-Path $postgresPath "data"

foreach ($scopedPath in @($releasePath, $environmentPath, $pythonPath, $postgresPath, [IO.Path]::GetFullPath($LogRoot))) {
    if (-not ($scopedPath -eq $installationPath -or $scopedPath.StartsWith($installationPath + "\", [StringComparison]::OrdinalIgnoreCase))) {
        throw "Deployment path is outside installation root ${installationPath}: $scopedPath"
    }
}

foreach ($requiredPath in @($scheduledLauncher, $processHelpers, $pgCtl, $dataRoot)) {
    if (-not (Test-Path -LiteralPath $requiredPath)) {
        throw "Required deployment path is missing: $requiredPath"
    }
}
. $processHelpers
New-Item -ItemType Directory -Path $LogRoot -Force | Out-Null

$taskNames = @("${DeploymentName}Web", "${DeploymentName}Worker")
foreach ($taskName in $taskNames) {
    if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
        Stop-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    }
}

$stopDeadline = [DateTime]::UtcNow.AddSeconds(30)
do {
    $runningTasks = @($taskNames | Where-Object {
        $task = Get-ScheduledTask -TaskName $_ -ErrorAction SilentlyContinue
        $task -and $task.State -ne "Ready"
    })
    if (-not $runningTasks.Count) { break }
    Start-Sleep -Milliseconds 500
} while ([DateTime]::UtcNow -lt $stopDeadline)
if ($runningTasks.Count) {
    throw "Scheduled tasks did not stop: $($runningTasks -join ', ')"
}

$allProcesses = @(Get-CimInstance Win32_Process)
$deploymentRoots = @(Get-RatRaceDeploymentProcessRoots `
    -Processes $allProcesses `
    -InstallationRoot $installationPath `
    -PythonExecutable $pythonPath)
$processesToStop = @(Get-RatRaceProcessTreeIds `
    -Processes $allProcesses `
    -RootProcessIds @($deploymentRoots | Select-Object -ExpandProperty ProcessId))
foreach ($processId in $processesToStop | Sort-Object -Descending) {
    Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
}
Start-Sleep -Seconds 1
$remainingRoots = @(Get-RatRaceDeploymentProcessRoots `
    -Processes @(Get-CimInstance Win32_Process) `
    -InstallationRoot $installationPath `
    -PythonExecutable $pythonPath)
if ($remainingRoots.Count) {
    $remainingIds = $remainingRoots.ProcessId -join ", "
    throw "Old $DeploymentName release processes remain after replacement: $remainingIds"
}

$postgresServiceName = "${DeploymentName}Postgres"
if (-not (Get-Service -Name $postgresServiceName -ErrorAction SilentlyContinue)) {
    & $pgCtl register `
        -D $dataRoot `
        -N $postgresServiceName `
        -S auto `
        -o "-h 127.0.0.1 -p $PostgresPort"
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

    $taskName = "${DeploymentName}$Process"
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
        "-Port $WebPort",
        "-DatabasePort $PostgresPort"
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

Start-ScheduledTask -TaskName "${DeploymentName}Web"
Start-ScheduledTask -TaskName "${DeploymentName}Worker"

foreach ($process in @("Web", "Worker")) {
    $processDeadline = [DateTime]::UtcNow.AddSeconds(30)
    do {
        Start-Sleep -Milliseconds 500
        $roots = @(Get-RatRaceDeploymentProcessRoots `
            -Processes @(Get-CimInstance Win32_Process) `
            -InstallationRoot $installationPath `
            -PythonExecutable $pythonPath `
            -Process $process)
        $task = Get-ScheduledTask -TaskName "${DeploymentName}$process"
        if ($roots.Count -and $task.State -eq "Running") { break }
    } while ([DateTime]::UtcNow -lt $processDeadline)
    if (-not $roots.Count -or $task.State -ne "Running") {
        throw "$DeploymentName $process task did not start its deployment process tree."
    }
    if ($roots.CommandLine -notmatch ([regex]::Escape($releasePath))) {
        throw "$DeploymentName $process is not running the requested release."
    }
}

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
    throw "Rat Race web readiness or worker heartbeat did not recover after startup-task cutover."
}

$result = [pscustomobject]@{
    PostgreSQL = (Get-Service -Name $postgresServiceName).Status.ToString()
    WebTask = (Get-ScheduledTask -TaskName "${DeploymentName}Web").State.ToString()
    WorkerTask = (Get-ScheduledTask -TaskName "${DeploymentName}Worker").State.ToString()
    Readiness = $readinessStatus
}
$result | ConvertTo-Json -Compress
