function Test-RatRacePathScope {
    param(
        [Parameter(Mandatory = $true)][string]$Candidate,
        [Parameter(Mandatory = $true)][string]$InstallationRoot
    )

    $root = [IO.Path]::GetFullPath($InstallationRoot).TrimEnd('\')
    $path = [IO.Path]::GetFullPath($Candidate)
    return $path -eq $root -or $path.StartsWith(
        $root + "\", [StringComparison]::OrdinalIgnoreCase
    )
}

function Get-RatRaceDeploymentProcessRoots {
    param(
        [Parameter(Mandatory = $true)][object[]]$Processes,
        [Parameter(Mandatory = $true)][string]$InstallationRoot,
        [string]$PythonExecutable = "",
        [ValidateSet("Web", "Worker", "Any")][string]$Process = "Any"
    )

    $installationPath = [IO.Path]::GetFullPath($InstallationRoot).TrimEnd('\')
    $pathPattern = [regex]::Escape($installationPath)
    $processPattern = if ($Process -eq "Any") {
        "-Process\s+(Web|Worker)(?:\s|$)"
    } else {
        "-Process\s+$Process(?:\s|$)"
    }
    $pythonPattern = if ($PythonExecutable) {
        [regex]::Escape([IO.Path]::GetFullPath($PythonExecutable))
    } else {
        "(?!)"
    }
    $runtimePattern = if ($Process -eq "Web") {
        "-m\s+uvicorn\s+config\.asgi:application"
    } elseif ($Process -eq "Worker") {
        "manage\.py\s+run_reference_update_worker"
    } else {
        "(-m\s+uvicorn\s+config\.asgi:application|manage\.py\s+run_reference_update_worker)"
    }
    $matches = @($Processes | Where-Object {
        $commandLine = $_.CommandLine
        $launcherMatch = (
            $commandLine -and
            $commandLine -match $pathPattern -and
            $commandLine -match "Start-RatRace(Scheduled)?Process\.ps1" -and
            $commandLine -match $processPattern
        )
        $runtimeMatch = (
            $commandLine -and
            $commandLine -match $pythonPattern -and
            $commandLine -match $runtimePattern
        )
        $launcherMatch -or $runtimeMatch
    })
    $matchIds = @($matches | Select-Object -ExpandProperty ProcessId)
    @($matches | Where-Object { $matchIds -notcontains $_.ParentProcessId })
}

function Get-RatRaceProcessTreeIds {
    param(
        [Parameter(Mandatory = $true)][object[]]$Processes,
        [int[]]$RootProcessIds = @()
    )

    $selected = New-Object System.Collections.Generic.HashSet[int]
    function Add-Descendants {
        param([int]$ProcessId)
        foreach ($child in $Processes | Where-Object ParentProcessId -eq $ProcessId) {
            Add-Descendants -ProcessId ([int]$child.ProcessId)
        }
        [void]$selected.Add($ProcessId)
    }
    foreach ($processId in $RootProcessIds) {
        Add-Descendants -ProcessId $processId
    }
    @($selected)
}
