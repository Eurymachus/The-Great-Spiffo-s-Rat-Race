param(
    [Parameter(Mandatory = $true)]
    [string]$PythonExecutable,

    [Parameter(Mandatory = $true)]
    [string]$ReleaseId,

    [string]$PostgresFragment = "C:\ProgramData\RatRace\config\postgres.generated.env",
    [string]$EnvironmentFile = "C:\ProgramData\RatRace\config\acceptance.env"
)

$ErrorActionPreference = "Stop"
$pythonPath = (Resolve-Path -LiteralPath $PythonExecutable).Path
$postgresPath = (Resolve-Path -LiteralPath $PostgresFragment).Path

$djangoSecret = & $pythonPath -c "import secrets; print(secrets.token_urlsafe(64))"
if ($LASTEXITCODE -or -not $djangoSecret) { throw "Unable to generate Django secret." }
$fernetKey = & $pythonPath -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
if ($LASTEXITCODE -or -not $fernetKey) { throw "Unable to generate Fernet key." }

$lines = @(
    "# ACCEPTANCE ENVIRONMENT ONLY - replace provider placeholders before public traffic"
    "DJANGO_SECRET_KEY=$djangoSecret"
    "DJANGO_ALLOWED_HOSTS=tgsrr.com,www.tgsrr.com,localhost,127.0.0.1"
    "DJANGO_CSRF_TRUSTED_ORIGINS=https://tgsrr.com,https://www.tgsrr.com"
    "DJANGO_SECURE_HSTS_SECONDS=3600"
    "DJANGO_LOG_LEVEL=INFO"
    "RELEASE_ID=$ReleaseId"
    "SITE_PUBLIC_URL=https://tgsrr.com"
    "RUNTIME_STATE_BACKEND=database"
    (Get-Content -LiteralPath $postgresPath)
    "POSTGRES_CONN_MAX_AGE=0"
    "EMAIL_HOST=127.0.0.1"
    "EMAIL_PORT=2525"
    "EMAIL_HOST_USER=ACCEPTANCE_ONLY_SMTP_USER"
    "EMAIL_HOST_PASSWORD=ACCEPTANCE_ONLY_SMTP_PASSWORD"
    "EMAIL_USE_TLS=false"
    "DEFAULT_FROM_EMAIL=The Great Spiffo's Rat Race <no-reply@tgsrr.com>"
    "SERVER_EMAIL=The Great Spiffo's Rat Race <no-reply@tgsrr.com>"
    "TURNSTILE_SITE_KEY=ACCEPTANCE_ONLY_TURNSTILE_SITE_KEY"
    "TURNSTILE_SECRET_KEY=ACCEPTANCE_ONLY_TURNSTILE_SECRET_KEY"
    "OPENAI_API_KEY=ACCEPTANCE_ONLY_OPENAI_API_KEY"
    "STREAMING_TOKEN_ENCRYPTION_KEY=$fernetKey"
    "TWITCH_CLIENT_ID=ACCEPTANCE_ONLY_TWITCH_CLIENT_ID"
    "TWITCH_CLIENT_SECRET=ACCEPTANCE_ONLY_TWITCH_CLIENT_SECRET"
    "TWITCH_REDIRECT_URI=https://tgsrr.com/account/streaming/twitch/callback/"
    "DISCORD_CLIENT_ID=ACCEPTANCE_ONLY_DISCORD_CLIENT_ID"
    "DISCORD_CLIENT_SECRET=ACCEPTANCE_ONLY_DISCORD_CLIENT_SECRET"
    "DISCORD_REDIRECT_URI=https://tgsrr.com/account/connections/discord/callback/"
    "YOUTUBE_CLIENT_ID=ACCEPTANCE_ONLY_YOUTUBE_CLIENT_ID"
    "YOUTUBE_CLIENT_SECRET=ACCEPTANCE_ONLY_YOUTUBE_CLIENT_SECRET"
    "YOUTUBE_REDIRECT_URI=https://tgsrr.com/account/streaming/youtube/callback/"
    "STEAMCMD_EXECUTABLE=G:\RatRace\steam\steamcmd.exe"
    "STEAMCMD_USERNAME=ACCEPTANCE_ONLY_STEAM_USERNAME"
    "STEAM_WEB_API_KEY=ACCEPTANCE_ONLY_STEAM_WEB_API_KEY"
    "PZ_REFERENCE_ROOT=G:\RatRace\reference"
    "JAVA_EXECUTABLE=C:\ProgramData\RatRace\bin\java\bin\java.exe"
    "VINEFLOWER_JAR=C:\ProgramData\RatRace\bin\vineflower.jar"
    "PZ_DECOMPILED_ROOT=G:\RatRace\decompiled"
    "STATIC_ROOT=C:\ProgramData\RatRace\static"
    "MEDIA_ROOT=G:\RatRace\media"
    "AVATAR_QUARANTINE_ROOT=G:\RatRace\private\avatars"
    "TRUST_CLOUDFLARE_CONNECTING_IP=true"
) | ForEach-Object { $_ }

$environmentPath = [System.IO.Path]::GetFullPath($EnvironmentFile)
New-Item -ItemType Directory -Path (Split-Path -Parent $environmentPath) -Force | Out-Null
[System.IO.File]::WriteAllLines($environmentPath, [string[]]$lines)
$currentIdentity = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
& icacls.exe $environmentPath /inheritance:r /grant:r `
    "Administrators:F" "SYSTEM:F" "${currentIdentity}:F" | Out-Null
if ($LASTEXITCODE) { throw "Unable to protect the acceptance environment file." }

Write-Output "Protected acceptance environment created: $environmentPath"
