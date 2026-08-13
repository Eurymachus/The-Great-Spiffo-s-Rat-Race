param(
    [Parameter(Mandatory = $true)]
    [string]$PythonExecutable,

    [Parameter(Mandatory = $true)]
    [string]$ReleaseId,

    [string]$InstallationRoot = "G:\RatRace_Staging",
    [string]$Hostname = "dev.tgsrr.com",
    [string]$PostgresFragment = "G:\RatRace_Staging\config\postgres.generated.env",
    [string]$EnvironmentFile = "G:\RatRace_Staging\config\staging.env"
)

$ErrorActionPreference = "Stop"
$root = [IO.Path]::GetFullPath($InstallationRoot).TrimEnd('\')
$pythonPath = (Resolve-Path -LiteralPath $PythonExecutable).Path
$postgresPath = (Resolve-Path -LiteralPath $PostgresFragment).Path
$environmentPath = [IO.Path]::GetFullPath($EnvironmentFile)
if (-not $environmentPath.StartsWith($root + "\", [StringComparison]::OrdinalIgnoreCase)) {
    throw "Environment file is outside staging installation root: $environmentPath"
}

$djangoSecret = & $pythonPath -c "import secrets; print(secrets.token_urlsafe(64))"
if ($LASTEXITCODE -or -not $djangoSecret) { throw "Unable to generate Django secret." }
$fernetKey = & $pythonPath -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
if ($LASTEXITCODE -or -not $fernetKey) { throw "Unable to generate Fernet key." }

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
    "# Provider credentials must be supplied separately before acceptance testing."
) | ForEach-Object { $_ }

New-Item -ItemType Directory -Path (Split-Path -Parent $environmentPath) -Force | Out-Null
[IO.File]::WriteAllLines($environmentPath, [string[]]$lines, [Text.UTF8Encoding]::new($false))
$currentIdentity = [Security.Principal.WindowsIdentity]::GetCurrent().Name
& icacls.exe $environmentPath /inheritance:r /grant:r `
    "Administrators:F" "SYSTEM:F" "${currentIdentity}:F" | Out-Null
if ($LASTEXITCODE) { throw "Unable to protect the staging environment file." }

Write-Output "Protected staging environment created: $environmentPath"
