param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("Web", "Worker")]
    [string]$Process,

    [Parameter(Mandatory = $true)]
    [string]$ReleaseRoot,

    [Parameter(Mandatory = $true)]
    [string]$EnvironmentFile,

    [Parameter(Mandatory = $true)]
    [string]$PythonExecutable,

    [Parameter(Mandatory = $true)]
    [string]$LogFile,

    [ValidateRange(1, 65535)]
    [int]$Port = 8000,

    [ValidateRange(1, 65535)]
    [int]$DatabasePort = 5432,

    [ValidateRange(1, 600)]
    [int]$DatabaseWaitSeconds = 300
)

$ErrorActionPreference = "Stop"
$launcher = Join-Path $PSScriptRoot "Start-RatRaceProcess.ps1"
$logPath = [System.IO.Path]::GetFullPath($LogFile)
$logDirectory = Split-Path -Parent $logPath
New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null

try {
    Add-Content -LiteralPath $logPath -Value (
        "{0:o} Starting Rat Race {1}." -f [DateTime]::UtcNow, $Process
    )
    $deadline = [DateTime]::UtcNow.AddSeconds($DatabaseWaitSeconds)
    do {
        $databaseReady = Test-NetConnection `
            -ComputerName 127.0.0.1 `
            -Port $DatabasePort `
            -InformationLevel Quiet `
            -WarningAction SilentlyContinue
        if ($databaseReady) { break }
        Start-Sleep -Seconds 5
    } while ([DateTime]::UtcNow -lt $deadline)

    if (-not $databaseReady) {
        throw "PostgreSQL did not become ready within $DatabaseWaitSeconds seconds."
    }

    $errorLogPath = [System.IO.Path]::ChangeExtension($logPath, ".error.log")
    $arguments = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", $launcher,
        "-Process", $Process,
        "-ReleaseRoot", $ReleaseRoot,
        "-EnvironmentFile", $EnvironmentFile,
        "-PythonExecutable", $PythonExecutable,
        "-Port", $Port
    )
    $child = Start-Process `
        -FilePath "powershell.exe" `
        -ArgumentList $arguments `
        -WindowStyle Hidden `
        -RedirectStandardOutput $logPath `
        -RedirectStandardError $errorLogPath `
        -Wait `
        -PassThru
    exit $child.ExitCode
} catch {
    Add-Content -LiteralPath $logPath -Value (
        "{0:o} Rat Race {1} startup failed: {2}" -f `
            [DateTime]::UtcNow, $Process, $_.Exception.Message
    )
    exit 1
}
