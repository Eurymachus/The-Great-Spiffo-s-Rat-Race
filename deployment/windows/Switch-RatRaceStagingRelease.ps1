param([Parameter(Mandatory=$true)][ValidatePattern('^[0-9a-f]{7,40}$')][string]$Release, [switch]$Initialize)
$ErrorActionPreference = 'Stop'
$root = 'G:\RatRace_StagingSecured'
$operation = if ($Initialize) { 'initialize' } else { 'switch' }
& (Join-Path $root 'venv\Scripts\python.exe') -E -B (Join-Path $root 'launchers\staging_release.py') $operation $Release
if ($LASTEXITCODE) { throw 'Staging release switch failed. Review the reported preparation/cutover/rollback result.' }
