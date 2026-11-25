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

    $releasePath = (Resolve-Path -LiteralPath $ReleaseRoot).Path
    $pythonPath = (Resolve-Path -LiteralPath $PythonExecutable).Path
    $logger = Join-Path $releasePath 'scripts\run_logged_process.py'
    if (-not (Test-Path -LiteralPath $logger -PathType Leaf)) {
        throw 'The release is missing its log rotation runner.'
    }
    & (Join-Path $PSScriptRoot 'Import-RatRaceEnvironment.ps1') -EnvironmentFile $EnvironmentFile
    Set-Location -LiteralPath (Join-Path $releasePath 'apps\website')
    $archiveRoot = Join-Path $logDirectory 'routine'
    New-Item -ItemType Directory -Path $archiveRoot -Force | Out-Null
    if ($Process -eq 'Web') {
        $childArguments = @('-u', '-m', 'uvicorn', 'config.asgi:application',
            '--host', '127.0.0.1', '--port', $Port, '--proxy-headers', '--forwarded-allow-ips', '127.0.0.1')
    } else {
        $childArguments = @('-u', 'manage.py', 'run_reference_update_worker')
    }
    & $pythonPath $logger --root $archiveRoot --label $Process.ToLowerInvariant() -- $pythonPath @childArguments
    exit $LASTEXITCODE
} catch {
    Add-Content -LiteralPath $logPath -Value (
        "{0:o} Rat Race {1} startup failed: {2}" -f `
            [DateTime]::UtcNow, $Process, $_.Exception.Message
    )
    exit 1
}
