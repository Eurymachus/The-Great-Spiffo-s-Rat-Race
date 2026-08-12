param(
    [Parameter(Mandatory = $true)]
    [string]$ReleaseRoot,

    [Parameter(Mandatory = $true)]
    [string]$EnvironmentFile,

    [Parameter(Mandatory = $true)]
    [string]$PythonExecutable
)

$ErrorActionPreference = "Stop"
$releasePath = (Resolve-Path -LiteralPath $ReleaseRoot).Path
$pythonPath = (Resolve-Path -LiteralPath $PythonExecutable).Path
$websitePath = Join-Path $releasePath "apps\website"
$environmentLoader = Join-Path $PSScriptRoot "Import-RatRaceEnvironment.ps1"

& $environmentLoader -EnvironmentFile $EnvironmentFile
Set-Location -LiteralPath $websitePath

& $pythonPath manage.py check --deploy
if ($LASTEXITCODE) { exit $LASTEXITCODE }
& $pythonPath manage.py check_production_deployment
exit $LASTEXITCODE
