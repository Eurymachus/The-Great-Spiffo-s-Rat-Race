param(
    [int]$Port = 8001,
    [switch]$Background
)

$workspacePath = if ($PSScriptRoot) {
    Split-Path -Parent $PSScriptRoot
} else {
    (Get-Location).Path
}
$environmentPath = Join-Path $workspacePath ".env"
$pythonPath = Join-Path $workspacePath ".venv\Scripts\python.exe"
$websitePath = Join-Path $workspacePath "apps\website"
$managePath = Join-Path $websitePath "manage.py"

if (-not (Test-Path -LiteralPath $environmentPath)) {
    throw "The local .env file is required."
}

Get-Content -LiteralPath $environmentPath | ForEach-Object {
    $line = $_.Trim()
    if ($line -and -not $line.StartsWith("#") -and $line.Contains("=")) {
        $parts = $line.Split("=", 2)
        $name = $parts[0].Trim()
        $value = $parts[1].Trim()
        if (
            ($value.StartsWith('"') -and $value.EndsWith('"')) -or
            ($value.StartsWith("'") -and $value.EndsWith("'"))
        ) {
            $value = $value.Substring(1, $value.Length - 2)
        }
        [Environment]::SetEnvironmentVariable($name, $value, "Process")
    }
}

$env:DJANGO_ALLOWED_HOSTS = "localhost,127.0.0.1,[::1],192.168.4.100"
Set-Location -LiteralPath $workspacePath
if ($Background) {
    Start-Process `
        -FilePath $pythonPath `
        -ArgumentList @("manage.py", "runserver", "0.0.0.0:$Port", "--noreload") `
        -WorkingDirectory $websitePath `
        -WindowStyle Hidden
    return
}

& $pythonPath $managePath runserver "0.0.0.0:$Port" --noreload
