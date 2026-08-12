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

    [ValidateRange(1, 65535)]
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"
$releasePath = (Resolve-Path -LiteralPath $ReleaseRoot).Path
$pythonPath = (Resolve-Path -LiteralPath $PythonExecutable).Path
$websitePath = Join-Path $releasePath "apps\website"
$environmentLoader = Join-Path $PSScriptRoot "Import-RatRaceEnvironment.ps1"

if (-not (Test-Path -LiteralPath (Join-Path $websitePath "manage.py"))) {
    throw "The release does not contain the Rat Race website."
}

& $environmentLoader -EnvironmentFile $EnvironmentFile
Set-Location -LiteralPath $websitePath

if ($Process -eq "Web") {
    & $pythonPath -m uvicorn config.asgi:application `
        --host 127.0.0.1 `
        --port $Port `
        --proxy-headers `
        --forwarded-allow-ips 127.0.0.1
} else {
    & $pythonPath manage.py run_reference_update_worker
}

exit $LASTEXITCODE
