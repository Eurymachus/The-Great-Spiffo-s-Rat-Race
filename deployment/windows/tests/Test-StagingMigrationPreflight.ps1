$ErrorActionPreference = 'Stop'
# Run the real preflight against temporary offline fixtures; never use host paths.
$temporary = Join-Path ([IO.Path]::GetTempPath()) ('staging-preflight-' + [guid]::NewGuid().ToString('N'))
$source = Join-Path $temporary 'source'
New-Item -ItemType Directory -Path $source -Force | Out-Null
try {
    foreach ($relative in @('config','venv\Scripts','releases\current\apps\website','pgdata','media','private','reference')) {
        New-Item -ItemType Directory -Path (Join-Path $source $relative) -Force | Out-Null
    }
    [IO.File]::WriteAllText("$source\venv\Scripts\python.exe", 'not executed')
    [IO.File]::WriteAllText("$source\pgdata\PG_VERSION", '17')
    [IO.File]::WriteAllText("$source\releases\current\apps\website\manage.py", '# fixture')
    $hash = (Get-FileHash "$source\releases\current\apps\website\manage.py").Hash.ToLowerInvariant()
    @{schema=1; commit=('a'*40); files=@{'apps/website/manage.py'=$hash}} | ConvertTo-Json -Depth 4 | Set-Content "$source\releases\current\staging-release.json"
    $environment = "POSTGRES_PORT=5433`nMEDIA_ROOT=$source\media`nAVATAR_QUARANTINE_ROOT=$source\private`nPZ_REFERENCE_ROOT=$source\reference`n"
    [IO.File]::WriteAllText("$source\config\staging.env", $environment)
    $code = [IO.File]::ReadAllText((Join-Path $PSScriptRoot '..\Move-RatRaceStagingHost.ps1'))
    $code = $code.Replace('G:\RatRace\_Staging',$source).Replace('G:\RatRace_StagingSecured',"$temporary\destination").Replace('G:\RatRace_StagingBackup',"$temporary\backup")
    $script = [scriptblock]::Create($code)
    function Get-CimInstance { @() }
    function Get-NetTCPConnection { @() }
    $report = & $script -Mode DryRun -CurrentCommit ('a'*40) -CurrentReleaseRelative 'releases\current' | ConvertFrom-Json
    if ($report.files -lt 4 -or (Test-Path "$temporary\destination") -or (Test-Path "$temporary\backup")) { throw 'Dry run mutated destination or missed inventory.' }
    foreach ($relative in @('..\production','C:\GSA','releases\..\..\outside')) {
        $rejected = $false
        try { & $script -CurrentCommit ('a'*40) -CurrentReleaseRelative $relative | Out-Null } catch { $rejected = $true }
        if (-not $rejected) { throw 'Migration accepted an arbitrary path.' }
    }
    [IO.File]::WriteAllText("$source\pgdata\postmaster.pid",'1')
    $rejected = $false
    try { & $script -CurrentCommit ('a'*40) -CurrentReleaseRelative 'releases\current' | Out-Null } catch { $rejected = $_.Exception.Message -match 'cleanly stopped' }
    if (-not $rejected) { throw 'Live cluster was accepted.' }
    [IO.File]::Delete("$source\pgdata\postmaster.pid")
    [IO.File]::WriteAllText("$source\config\staging.env", $environment.Replace('5433','5432'))
    $rejected = $false
    try { & $script -CurrentCommit ('a'*40) -CurrentReleaseRelative 'releases\current' | Out-Null } catch { $rejected = $_.Exception.Message -match '5433' }
    if (-not $rejected) { throw 'Production database port was accepted.' }
    Write-Output 'Migration preflight and dry-run fixtures passed.'
} finally {
    $resolved = [IO.Path]::GetFullPath($temporary)
    if (-not $resolved.StartsWith([IO.Path]::GetFullPath([IO.Path]::GetTempPath()),[StringComparison]::OrdinalIgnoreCase) -or [IO.Path]::GetFileName($resolved) -notlike 'staging-preflight-*') { throw 'Unsafe fixture cleanup path.' }
    Remove-Item -LiteralPath $resolved -Recurse -Force
}
