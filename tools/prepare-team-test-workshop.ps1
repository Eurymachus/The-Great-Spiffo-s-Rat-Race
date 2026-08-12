param(
    [string]$OutputPath = "outputs/team-test-workshop",
    [string]$WorkshopId = ""
)

$ErrorActionPreference = "Stop"

$repositoryRoot = Split-Path -Parent $PSScriptRoot
$resolvedOutput = Join-Path $repositoryRoot $OutputPath
$contentsSource = Join-Path $repositoryRoot "Contents"
$previewSource = Join-Path $repositoryRoot "preview.png"
$metadataTemplate = Join-Path $PSScriptRoot "team-test-workshop.txt"

if (Test-Path -LiteralPath $resolvedOutput) {
    Remove-Item -LiteralPath $resolvedOutput -Recurse -Force
}

New-Item -ItemType Directory -Path $resolvedOutput | Out-Null
Copy-Item -LiteralPath $contentsSource -Destination $resolvedOutput -Recurse
Copy-Item -LiteralPath $previewSource -Destination $resolvedOutput

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
Write-Output "Files: $fileCount"
Write-Output "Bytes: $totalBytes"
