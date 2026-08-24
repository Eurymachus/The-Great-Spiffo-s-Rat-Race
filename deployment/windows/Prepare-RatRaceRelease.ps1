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
$managePath = Join-Path $websitePath "manage.py"
$environmentLoader = Join-Path $PSScriptRoot "Import-RatRaceEnvironment.ps1"

if (-not (Test-Path -LiteralPath $managePath -PathType Leaf)) {
    throw "The release does not contain the Rat Race website."
}

& $environmentLoader -EnvironmentFile $EnvironmentFile
Set-Location -LiteralPath $websitePath

& $pythonPath manage.py migrate --noinput
if ($LASTEXITCODE) { exit $LASTEXITCODE }

& $pythonPath manage.py bootstrap_roles
if ($LASTEXITCODE) { exit $LASTEXITCODE }

& $pythonPath manage.py collectstatic --noinput
exit $LASTEXITCODE
