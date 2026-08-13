param(
    [Parameter(Mandatory = $true)]
    [string]$PythonExecutable,

    [Parameter(Mandatory = $true)]
    [string]$ReleaseId,

    [string]$InstallationRoot = "G:\RatRace_Staging",
    [string]$Hostname = "dev.tgsrr.com",
    [string]$PostgresFragment = "G:\RatRace_Staging\config\postgres.generated.env",
    [string]$SourceEnvironmentFile = "G:\RatRace\config\acceptance.env",
    [string]$EnvironmentFile = "G:\RatRace_Staging\config\staging.env"
)

$ErrorActionPreference = "Stop"
$root = [IO.Path]::GetFullPath($InstallationRoot).TrimEnd('\')
$pythonPath = (Resolve-Path -LiteralPath $PythonExecutable).Path
$postgresPath = (Resolve-Path -LiteralPath $PostgresFragment).Path
$sourcePath = (Resolve-Path -LiteralPath $SourceEnvironmentFile).Path
$environmentPath = [IO.Path]::GetFullPath($EnvironmentFile)
if (-not $environmentPath.StartsWith($root + "\", [StringComparison]::OrdinalIgnoreCase)) {
    throw "Environment file is outside staging installation root: $environmentPath"
}

$djangoSecret = & $pythonPath -c "import secrets; print(secrets.token_urlsafe(64))"
if ($LASTEXITCODE -or -not $djangoSecret) { throw "Unable to generate Django secret." }
$fernetKey = & $pythonPath -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
if ($LASTEXITCODE -or -not $fernetKey) { throw "Unable to generate Fernet key." }

$source = @{}
Get-Content -LiteralPath $sourcePath | ForEach-Object {
    $line = $_.Trim()
    if (-not $line -or $line.StartsWith("#") -or -not $line.Contains("=")) { return }
    $name, $value = $line.Split("=", 2)
    $source[$name.Trim()] = $value
}
$copiedNames = @(
    "MICROSOFT_GRAPH_TENANT_ID", "MICROSOFT_GRAPH_CLIENT_ID",
    "MICROSOFT_GRAPH_CLIENT_SECRET", "MICROSOFT_GRAPH_SENDER",
    "MICROSOFT_GRAPH_REPLY_TO", "DEFAULT_FROM_EMAIL", "OPENAI_API_KEY",
    "TWITCH_CLIENT_ID", "TWITCH_CLIENT_SECRET", "DISCORD_CLIENT_ID",
    "DISCORD_CLIENT_SECRET", "YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET",
    "STEAMCMD_USERNAME", "STEAM_WEB_API_KEY"
)
$missingCopied = @($copiedNames | Where-Object { -not $source[$_] })
if ($missingCopied.Count) {
    throw "Source environment is missing required integration values: $($missingCopied -join ', ')"
}

$lines = @(
    "# STAGING ENVIRONMENT - isolated from production"
    "DJANGO_SECRET_KEY=$djangoSecret"
    "DJANGO_SETTINGS_MODULE=config.settings_windows_staging"
    "DJANGO_ALLOWED_HOSTS=$Hostname,localhost,127.0.0.1"
    "DJANGO_CSRF_TRUSTED_ORIGINS=https://$Hostname"
    "DJANGO_SECURE_HSTS_SECONDS=3600"
    "DJANGO_LOG_LEVEL=INFO"
    "RELEASE_ID=$ReleaseId"
    "SITE_PUBLIC_URL=https://$Hostname"
    "RUNTIME_STATE_BACKEND=database"
    (Get-Content -LiteralPath $postgresPath)
    "POSTGRES_CONN_MAX_AGE=60"
    "STATIC_ROOT=$root\static"
    "MEDIA_ROOT=$root\media"
    "AVATAR_QUARANTINE_ROOT=$root\private\avatars"
    "PZ_REFERENCE_ROOT=$root\reference"
    "PZ_DECOMPILED_ROOT=$root\decompiled"
    "STREAMING_TOKEN_ENCRYPTION_KEY=$fernetKey"
    "TRUST_CLOUDFLARE_CONNECTING_IP=true"
    "STAGING_ENVIRONMENT=true"
    "STAGING_EMAIL_ALLOWLIST=eury@machus.co.uk,greg.jones@sentineltech.co.uk"
    "TURNSTILE_SITE_KEY=1x00000000000000000000AA"
    "TURNSTILE_SECRET_KEY=1x0000000000000000000000000000000AA"
    "TWITCH_REDIRECT_URI=https://$Hostname/account/streaming/twitch/callback/"
    "DISCORD_REDIRECT_URI=https://$Hostname/account/connections/discord/callback/"
    "YOUTUBE_REDIRECT_URI=https://$Hostname/account/streaming/youtube/callback/"
    "STEAMCMD_EXECUTABLE=$root\steam\steamcmd.exe"
    "JAVA_EXECUTABLE=$root\runtime\java\bin\java.exe"
    "VINEFLOWER_JAR=$root\runtime\vineflower.jar"
) | ForEach-Object { $_ }
$lines += $copiedNames | ForEach-Object { "$_=$($source[$_])" }

New-Item -ItemType Directory -Path (Split-Path -Parent $environmentPath) -Force | Out-Null
[IO.File]::WriteAllLines($environmentPath, [string[]]$lines, [Text.UTF8Encoding]::new($false))
$currentIdentity = [Security.Principal.WindowsIdentity]::GetCurrent().Name
& icacls.exe $environmentPath /inheritance:r /grant:r `
    "Administrators:F" "SYSTEM:F" "${currentIdentity}:F" | Out-Null
if ($LASTEXITCODE) { throw "Unable to protect the staging environment file." }

Write-Output "Protected staging environment created: $environmentPath"
