param(
    [string]$OutputPath = "outputs/team-test-workshop",
    [string]$WorkshopId = "3782093082"
)

$ErrorActionPreference = "Stop"

$repositoryRoot = Split-Path -Parent $PSScriptRoot
$resolvedOutput = if ([System.IO.Path]::IsPathRooted($OutputPath)) {
    $OutputPath
} else {
    Join-Path $repositoryRoot $OutputPath
}
$modSource = Join-Path $repositoryRoot "Contents/mods/Great Spiffo's Rat Race"
$previewSource = Join-Path $repositoryRoot "preview.png"
$metadataTemplate = Join-Path $PSScriptRoot "team-test-workshop.txt"

if (Test-Path -LiteralPath $resolvedOutput) {
    Remove-Item -LiteralPath $resolvedOutput -Recurse -Force
}

New-Item -ItemType Directory -Path $resolvedOutput | Out-Null
$modOutput = Join-Path $resolvedOutput "Contents/mods/Great Spiffo's Rat Race"
New-Item -ItemType Directory -Path (Split-Path -Parent $modOutput) -Force | Out-Null
Copy-Item -LiteralPath $modSource -Destination $modOutput -Recurse
Copy-Item -LiteralPath $previewSource -Destination $resolvedOutput

$testModInfoPaths = Get-ChildItem -LiteralPath $modOutput -Recurse -File -Filter "mod.info"
foreach ($testModInfoPath in $testModInfoPaths) {
    $testModInfo = Get-Content -LiteralPath $testModInfoPath.FullName
    $testModInfo = $testModInfo | ForEach-Object {
        if ($_ -match '^id=') {
            "id=TGSRR-test"
        } elseif ($_ -match '^name=') {
            "name=The Great Spiffo's Rat Race - Team Test"
        } else {
            $_
        }
    }
    Set-Content -LiteralPath $testModInfoPath.FullName -Value $testModInfo -Encoding UTF8
}

$metadata = Get-Content -LiteralPath $metadataTemplate
$metadata = $metadata | ForEach-Object {
    if ($_ -match '^id=') {
        "id=$WorkshopId"
    } else {
        $_
    }
}
Set-Content -LiteralPath (Join-Path $resolvedOutput "workshop.txt") -Value $metadata -Encoding UTF8

$fileCount = (Get-ChildItem -LiteralPath $resolvedOutput -Recurse -File).Count
$totalBytes = (Get-ChildItem -LiteralPath $resolvedOutput -Recurse -File | Measure-Object -Property Length -Sum).Sum

Write-Output "Prepared unlisted team-test Workshop package: $resolvedOutput"
Write-Output "Workshop ID: $(if ($WorkshopId) { $WorkshopId } else { '<new item>' })"
Write-Output "Mod ID: TGSRR-test"
Write-Output "Files: $fileCount"
Write-Output "Bytes: $totalBytes"
