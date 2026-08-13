param(
    [Parameter(Mandatory = $true)]
    [string]$EnvironmentFile
)

$resolvedEnvironmentFile = (Resolve-Path -LiteralPath $EnvironmentFile).Path
Get-Content -LiteralPath $resolvedEnvironmentFile | ForEach-Object {
    $line = $_.Trim()
    if (-not $line -or $line.StartsWith("#")) {
        return
    }
    if (-not $line.Contains("=")) {
        throw "Invalid production environment entry."
    }
    $parts = $line.Split("=", 2)
    $name = $parts[0].Trim()
    $value = $parts[1].Trim()
    if ($name -notmatch '^[A-Z][A-Z0-9_]*$') {
        throw "Invalid production environment variable name."
    }
    if (
        $value.Length -ge 2 -and
        (($value.StartsWith('"') -and $value.EndsWith('"')) -or
         ($value.StartsWith("'") -and $value.EndsWith("'")))
    ) {
        $value = $value.Substring(1, $value.Length - 2)
    }
    [Environment]::SetEnvironmentVariable($name, $value, "Process")
}

if (-not $env:DJANGO_SETTINGS_MODULE) {
    $env:DJANGO_SETTINGS_MODULE = "config.settings_windows_production"
}
$env:RUNTIME_STATE_BACKEND = "database"
