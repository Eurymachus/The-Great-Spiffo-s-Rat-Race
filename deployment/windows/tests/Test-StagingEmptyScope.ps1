$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\RatRaceProcessHelpers.ps1')
# Empty property expansion can coerce null to PID 0 in Windows PowerShell.
$roots = @()
$rootIds = @($roots | Where-Object { $_.ProcessId -gt 0 } | Select-Object -ExpandProperty ProcessId)
$processes = @(
    [pscustomobject]@{ProcessId=10;ParentProcessId=0;CommandLine='production'},
    [pscustomobject]@{ProcessId=20;ParentProcessId=10;CommandLine='GSA'}
)
$ids = @(Get-RatRaceProcessTreeIds -Processes $processes -RootProcessIds $rootIds)
if ($ids.Count -ne 0) { throw 'Empty staging scope selected unrelated processes.' }
$rejected = $false
try { Get-RatRaceProcessTreeIds -Processes $processes -RootProcessIds @(0) | Out-Null } catch { $rejected = $true }
if (-not $rejected) { throw 'PID 0 must be rejected.' }
$other = @([pscustomobject]@{ProcessId=99;ParentProcessId=1;CommandLine='powershell G:\RatRace\_StagingOther\Start-RatRaceProcess.ps1 -Process Web'})
$matched = @(Get-RatRaceDeploymentProcessRoots -Processes $other -InstallationRoot 'G:\RatRace\_Staging')
if ($matched.Count) { throw 'Sibling installation entered staging scope.' }
Write-Output 'Empty staging process scope passed.'
