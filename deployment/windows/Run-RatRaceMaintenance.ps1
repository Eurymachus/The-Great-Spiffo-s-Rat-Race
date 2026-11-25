param(
    [Parameter(Mandatory = $true)][string]$ReleaseRoot,
    [Parameter(Mandatory = $true)][string]$EnvironmentFile,
    [Parameter(Mandatory = $true)][string]$PythonExecutable,
    [Parameter(Mandatory = $true)][string]$BackupRoot,
    [Parameter(Mandatory = $true)][string]$RoutineLogRoot,
    [Parameter(Mandatory = $true)][string]$PostgresBin,
    [Parameter(Mandatory = $true)][string]$ReleaseId,
    [string[]]$SourceDirectories = @(),
    [switch]$Capture,
    [switch]$Apply
)
$ErrorActionPreference = 'Stop'
$releasePath = (Resolve-Path -LiteralPath $ReleaseRoot).Path
$pythonPath = (Resolve-Path -LiteralPath $PythonExecutable).Path
$artifactTool = Join-Path $releasePath 'scripts\host_artifacts.py'
$retentionTool = Join-Path $releasePath 'deployment\windows\Run-RatRaceRetention.ps1'
foreach ($path in @($artifactTool, $retentionTool, $BackupRoot, $RoutineLogRoot, $PostgresBin, $EnvironmentFile)) {
    if (-not (Test-Path -LiteralPath $path)) { throw 'A reviewed maintenance path is missing.' }
}
if ($Apply -and -not $Capture) {
    throw 'Apply requires a successful capture in this same invocation.'
}
if ($Capture) {
    $captureArguments = @($artifactTool, 'capture', '--root', $BackupRoot,
        '--environment', $EnvironmentFile, '--pg-bin', $PostgresBin, '--release', $ReleaseId)
    foreach ($source in $SourceDirectories) { $captureArguments += @('--source', $source) }
    & $pythonPath @captureArguments
    if ($LASTEXITCODE) { exit $LASTEXITCODE }
} else {
    Write-Output 'Preview only: no backup created and no data or artifacts deleted.'
}
$retentionArguments = @{
    ReleaseRoot = $releasePath
    EnvironmentFile = $EnvironmentFile
    PythonExecutable = $pythonPath
    Apply = $Apply
}
& $retentionTool @retentionArguments
if ($LASTEXITCODE) { exit $LASTEXITCODE }
foreach ($root in @($BackupRoot, $RoutineLogRoot)) {
    $expiryArguments = @($artifactTool, 'expire', '--root', $root)
    if ($Apply) { $expiryArguments += '--apply' }
    & $pythonPath @expiryArguments
    if ($LASTEXITCODE) { exit $LASTEXITCODE }
}
exit 0
