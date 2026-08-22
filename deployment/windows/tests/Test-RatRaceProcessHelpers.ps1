$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "..\RatRaceProcessHelpers.ps1")

function Assert-Equal($Expected, $Actual, $Message) {
    if ($Expected -ne $Actual) {
        throw "$Message Expected '$Expected', got '$Actual'."
    }
}

$processes = @(
    [pscustomobject]@{ ProcessId = 10; ParentProcessId = 1; CommandLine = 'powershell -File "G:\RatRace_Staging\releases\abc\deployment\windows\Start-RatRaceScheduledProcess.ps1" -Process Web' }
    [pscustomobject]@{ ProcessId = 11; ParentProcessId = 10; CommandLine = 'powershell -File "G:\RatRace_Staging\releases\abc\deployment\windows\Start-RatRaceProcess.ps1" -Process Web' }
    [pscustomobject]@{ ProcessId = 12; ParentProcessId = 11; CommandLine = 'python -m uvicorn config.asgi:application' }
    [pscustomobject]@{ ProcessId = 13; ParentProcessId = 1; CommandLine = '"G:\RatRace_Staging\venv\Scripts\python.exe" -m uvicorn config.asgi:application' }
    [pscustomobject]@{ ProcessId = 20; ParentProcessId = 1; CommandLine = 'powershell -File "G:\RatRace\releases\abc\deployment\windows\Start-RatRaceScheduledProcess.ps1" -Process Web' }
    [pscustomobject]@{ ProcessId = 30; ParentProcessId = 1; CommandLine = 'powershell C:\GSA\worker.ps1' }
    [pscustomobject]@{ ProcessId = 40; ParentProcessId = 1; CommandLine = 'python unrelated.py' }
)

$roots = @(Get-RatRaceDeploymentProcessRoots `
    -Processes $processes `
    -InstallationRoot 'G:\RatRace_Staging' `
    -PythonExecutable 'G:\RatRace_Staging\venv\Scripts\python.exe' `
    -Process Web)
Assert-Equal 2 $roots.Count "The staging wrapper and orphaned web runtime should match."
if ($roots.ProcessId -notcontains 10 -or $roots.ProcessId -notcontains 13) {
    throw "The expected staging wrapper and orphaned runtime were not selected."
}

$tree = @(Get-RatRaceProcessTreeIds -Processes $processes -RootProcessIds $roots.ProcessId)
Assert-Equal 4 $tree.Count "The complete staging tree and orphan should be selected."
foreach ($excluded in 20, 30, 40) {
    if ($tree -contains $excluded) {
        throw "Process $excluded escaped deployment scoping."
    }
}

Assert-Equal $true (Test-RatRacePathScope 'G:\RatRace_Staging\logs' 'G:\RatRace_Staging') "A child path should be accepted."
Assert-Equal $false (Test-RatRacePathScope 'G:\RatRace\logs' 'G:\RatRace_Staging') "Production should be rejected from staging scope."
Write-Output "Rat Race process helper tests passed."
