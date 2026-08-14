param(
    [Parameter(Mandatory = $true)]
    [string]$EnvironmentFile,

    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[A-Z][A-Z0-9_]*$')]
    [string]$Name,

    [Parameter(Mandatory = $true)]
    [AllowEmptyString()]
    [string]$Value
)

$ErrorActionPreference = "Stop"
$environmentPath = (Resolve-Path -LiteralPath $EnvironmentFile).Path
$lines = [Collections.Generic.List[string]](
    Get-Content -LiteralPath $environmentPath
)
$replacement = "$Name=$Value"
$matches = @(
    for ($index = 0; $index -lt $lines.Count; $index++) {
        if ($lines[$index] -match "^$([regex]::Escape($Name))=") { $index }
    }
)
if ($matches.Count -gt 1) {
    throw "Environment file contains duplicate $Name entries."
}
if ($matches.Count -eq 1) {
    $lines[$matches[0]] = $replacement
} else {
    $lines.Add($replacement)
}
[IO.File]::WriteAllLines(
    $environmentPath,
    [string[]]$lines,
    [Text.UTF8Encoding]::new($false)
)
