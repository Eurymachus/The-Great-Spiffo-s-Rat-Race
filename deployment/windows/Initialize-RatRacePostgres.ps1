param(
    [string]$InstallationRoot = "G:\RatRace",
    [string]$RuntimeRoot = "G:\RatRace\postgres\runtime\pgsql",
    [string]$DataRoot = "G:\RatRace\postgres\data",
    [string]$EnvironmentFragment = "C:\ProgramData\RatRace\config\postgres.generated.env",
    [ValidateRange(1, 65535)]
    [int]$Port = 5432
)

$ErrorActionPreference = "Stop"
$binPath = Join-Path $RuntimeRoot "bin"
$initdb = Join-Path $binPath "initdb.exe"
$pgCtl = Join-Path $binPath "pg_ctl.exe"
$psql = Join-Path $binPath "psql.exe"

foreach ($executable in ($initdb, $pgCtl, $psql)) {
    if (-not (Test-Path -LiteralPath $executable -PathType Leaf)) {
        throw "Required PostgreSQL executable is missing: $executable"
    }
}

$dataPath = [System.IO.Path]::GetFullPath($DataRoot)
$installationPath = [System.IO.Path]::GetFullPath($InstallationRoot).TrimEnd('\')
$expectedDataPath = Join-Path $installationPath "postgres\data"
if ($dataPath -ne $expectedDataPath) {
    throw "Refusing unexpected PostgreSQL data path: $dataPath"
}
if ((Get-ChildItem -LiteralPath $dataPath -Force | Measure-Object).Count -ne 0) {
    throw "PostgreSQL data directory is not empty."
}

function New-RandomHex([int]$Bytes = 32) {
    $buffer = [byte[]]::new($Bytes)
    $generator = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $generator.GetBytes($buffer)
    } finally {
        $generator.Dispose()
    }
    return ([BitConverter]::ToString($buffer) -replace "-", "").ToLowerInvariant()
}

$postgresPassword = New-RandomHex
$applicationPassword = New-RandomHex
$temporaryPasswordFile = Join-Path $env:TEMP ("rat-race-pg-" + [guid]::NewGuid() + ".txt")

try {
    [System.IO.File]::WriteAllText($temporaryPasswordFile, $postgresPassword + [Environment]::NewLine)
    & $initdb `
        --pgdata=$dataPath `
        --username=postgres `
        --pwfile=$temporaryPasswordFile `
        --auth-local=scram-sha-256 `
        --auth-host=scram-sha-256 `
        --encoding=UTF8 `
        --locale=C
    if ($LASTEXITCODE) { throw "initdb failed with exit code $LASTEXITCODE." }
} finally {
    Remove-Item -LiteralPath $temporaryPasswordFile -Force -ErrorAction SilentlyContinue
}

$logPath = Join-Path $installationPath "logs\postgres.log"
New-Item -ItemType Directory -Path (Split-Path -Parent $logPath) -Force | Out-Null
& $pgCtl -D $dataPath -l $logPath -o "-h 127.0.0.1 -p $Port" start
if ($LASTEXITCODE) { throw "PostgreSQL startup failed with exit code $LASTEXITCODE." }

$previousPassword = $env:PGPASSWORD
try {
    $env:PGPASSWORD = $postgresPassword
    & $psql -h 127.0.0.1 -p $Port -U postgres -d postgres `
        -v ON_ERROR_STOP=1 `
        -c "CREATE ROLE ratrace LOGIN PASSWORD '$applicationPassword';"
    if ($LASTEXITCODE) { throw "Creating the application role failed." }
    & $psql -h 127.0.0.1 -p $Port -U postgres -d postgres `
        -v ON_ERROR_STOP=1 `
        -c "CREATE DATABASE ratrace OWNER ratrace;"
    if ($LASTEXITCODE) { throw "Creating the application database failed." }
} finally {
    $env:PGPASSWORD = $previousPassword
}

$fragmentPath = [System.IO.Path]::GetFullPath($EnvironmentFragment)
$fragmentDirectory = Split-Path -Parent $fragmentPath
New-Item -ItemType Directory -Path $fragmentDirectory -Force | Out-Null
$fragment = @(
    "POSTGRES_DB=ratrace"
    "POSTGRES_USER=ratrace"
    "POSTGRES_PASSWORD=$applicationPassword"
    "POSTGRES_HOST=127.0.0.1"
    "POSTGRES_PORT=$Port"
    "POSTGRES_SSLMODE=disable"
) -join [Environment]::NewLine
[System.IO.File]::WriteAllText($fragmentPath, $fragment + [Environment]::NewLine)
$currentIdentity = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
& icacls.exe $fragmentPath /inheritance:r /grant:r `
    "Administrators:F" "SYSTEM:F" "${currentIdentity}:F" | Out-Null
if ($LASTEXITCODE) { throw "Unable to protect the PostgreSQL environment fragment." }

Write-Output "PostgreSQL initialized for Rat Race on 127.0.0.1:$Port."
Write-Output "Application environment fragment: $fragmentPath"
