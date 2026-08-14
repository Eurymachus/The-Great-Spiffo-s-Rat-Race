param(
    [Parameter(Mandatory = $true)]
    [string]$ReleaseRoot,

    [string]$InstallationRoot = "G:\RatRace_Staging"
)

$ErrorActionPreference = "Stop"
$releasePath = (Resolve-Path -LiteralPath $ReleaseRoot).Path
$root = (Resolve-Path -LiteralPath $InstallationRoot).Path
$installer = Join-Path $releasePath "deployment\windows\Install-RatRaceStartup.ps1"

& $installer `
    -InstallationRoot $root `
    -DeploymentName "RatRaceStaging" `
    -ReleaseRoot $releasePath `
    -EnvironmentFile (Join-Path $root "config\staging.env") `
    -PythonExecutable (Join-Path $root "venv\Scripts\python.exe") `
    -PostgresRoot (Join-Path $root "postgres") `
    -LogRoot (Join-Path $root "logs") `
    -WebPort 8002 `
    -PostgresPort 5433

exit $LASTEXITCODE
