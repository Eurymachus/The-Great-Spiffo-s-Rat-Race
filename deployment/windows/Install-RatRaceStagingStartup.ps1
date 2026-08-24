param(
    [Parameter(Mandatory = $true)]
    [string]$ReleaseRoot,

    [string]$InstallationRoot = "G:\RatRace_Staging"
)

$ErrorActionPreference = "Stop"
$releasePath = (Resolve-Path -LiteralPath $ReleaseRoot).Path
$root = (Resolve-Path -LiteralPath $InstallationRoot).Path
$preparer = Join-Path $releasePath "deployment\windows\Prepare-RatRaceRelease.ps1"
$installer = Join-Path $releasePath "deployment\windows\Install-RatRaceStartup.ps1"
$environmentFile = Join-Path $root "config\staging.env"
$pythonExecutable = Join-Path $root "venv\Scripts\python.exe"

& $preparer `
    -ReleaseRoot $releasePath `
    -EnvironmentFile $environmentFile `
    -PythonExecutable $pythonExecutable
if ($LASTEXITCODE) { exit $LASTEXITCODE }

& $installer `
    -InstallationRoot $root `
    -DeploymentName "RatRaceStaging" `
    -ReleaseRoot $releasePath `
    -EnvironmentFile $environmentFile `
    -PythonExecutable $pythonExecutable `
    -PostgresRoot (Join-Path $root "postgres") `
    -LogRoot (Join-Path $root "logs") `
    -WebPort 8002 `
    -PostgresPort 5433

exit $LASTEXITCODE
