param(
    [Parameter(Mandatory = $true)]
    [string]$CsvPath,

    [Parameter(Mandatory = $true)]
    [string]$OutputPath
)

$rows = Import-Csv -LiteralPath $CsvPath
$lines = [System.Collections.Generic.List[string]]::new()
$lines.Add("-- Generated from Random Spawn Locations - Spawns.csv.")
$lines.Add("-- Regenerate with tools/generate-rsl-building-id-data.ps1; do not edit by hand.")
$lines.Add("return {")

foreach ($row in $rows) {
    $id = [int]$row.ID
    $x = [int]$row.X
    $y = [int]$row.Y
    $z = [int]$row.Z
    $note = [string]$row.Note
    $note = $note.Replace("\", "\\").Replace('"', '\"').Replace("`r", " ").Replace("`n", " ")
    $lines.Add("    { id=$id, x=$x, y=$y, z=$z, note=`"$note`" },")
}

$lines.Add("}")
$outputDirectory = Split-Path -Parent $OutputPath
if ($outputDirectory -and -not (Test-Path -LiteralPath $outputDirectory)) {
    New-Item -ItemType Directory -Path $outputDirectory | Out-Null
}
[System.IO.File]::WriteAllLines($OutputPath, $lines, [System.Text.UTF8Encoding]::new($false))
Write-Output "Generated $($rows.Count) records at $OutputPath"
