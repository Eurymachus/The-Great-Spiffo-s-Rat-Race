param(
    [Parameter(Mandatory = $true)][string]$ReleaseRoot,
    [Parameter(Mandatory = $true)][string]$EnvironmentFile,
    [Parameter(Mandatory = $true)][string]$PythonExecutable,
    [switch]$Apply
)

$ErrorActionPreference = "Stop"
$releasePath = (Resolve-Path -LiteralPath $ReleaseRoot).Path
$pythonPath = (Resolve-Path -LiteralPath $PythonExecutable).Path
$managePath = Join-Path $releasePath "apps\website\manage.py"
if (-not (Test-Path -LiteralPath $managePath -PathType Leaf)) {
    throw "The release does not contain the Rat Race website."
}

& (Join-Path $PSScriptRoot "Import-RatRaceEnvironment.ps1") -EnvironmentFile $EnvironmentFile
$retentionArguments = @($managePath, "apply_account_retention")
if ($Apply) { $retentionArguments += "--apply" }
& $pythonPath @retentionArguments
$accountRetentionExit = $LASTEXITCODE
$evidenceArguments = @($managePath, "apply_evidence_retention")
if ($Apply) { $evidenceArguments += "--apply" }
& $pythonPath @evidenceArguments
$evidenceRetentionExit = $LASTEXITCODE
$runtimeArguments = @($managePath, "prune_runtime_state")
if ($Apply) { $runtimeArguments += "--apply" }
& $pythonPath @runtimeArguments
$runtimeRetentionExit = $LASTEXITCODE
if ($accountRetentionExit) { exit $accountRetentionExit }
if ($evidenceRetentionExit) { exit $evidenceRetentionExit }
exit $runtimeRetentionExit
