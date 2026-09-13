$ErrorActionPreference = 'Stop'
# Run the real preflight against temporary offline fixtures; never use host paths.
$temporary = Join-Path ([IO.Path]::GetTempPath()) ('staging-preflight-' + [guid]::NewGuid().ToString('N'))
$source = Join-Path $temporary 'source'
New-Item -ItemType Directory -Path $source -Force | Out-Null
try {
    foreach ($relative in @('config','venv\Scripts','releases','pgdata','media','private','reference')) {
        New-Item -ItemType Directory -Path (Join-Path $source $relative) -Force | Out-Null
    }
    [IO.File]::WriteAllText("$source\venv\Scripts\python.exe", 'not executed')
    [IO.File]::WriteAllText("$source\pgdata\PG_VERSION", '17')
    $checkout = Join-Path $temporary 'reviewed'
    New-Item -ItemType Directory -Path "$checkout\apps\website\config" -Force | Out-Null
    foreach ($file in @('manage.py','config\asgi.py','config\settings_windows_staging.py')) { [IO.File]::WriteAllText((Join-Path "$checkout\apps\website" $file),'# fixture') }
    & git init -q $checkout
    & git -C $checkout add .
    & git -C $checkout -c user.name=Fixture -c user.email=fixture@example.invalid commit -qm fixture
    $commit = & git -C $checkout rev-parse HEAD
    & git -C $checkout update-ref refs/remotes/origin/codex/rat-race-dev $commit
    $relativeRelease = 'releases\' + $commit.Substring(0,7)
    $legacy = Join-Path $source $relativeRelease
    & git -C $checkout archive --format=zip "--output=$temporary\fixture.zip" $commit
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    [IO.Compression.ZipFile]::ExtractToDirectory("$temporary\fixture.zip",$legacy)
    $environment = "POSTGRES_PORT=5433`nMEDIA_ROOT=$source\media`nAVATAR_QUARANTINE_ROOT=$source\private`nPZ_REFERENCE_ROOT=$source\reference`n"
    [IO.File]::WriteAllText("$source\config\staging.env", $environment)
    $code = [IO.File]::ReadAllText((Join-Path $PSScriptRoot '..\Move-RatRaceStagingHost.ps1'))
    $helper = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\Test-RatRaceLegacyRelease.ps1'))
    $code = $code.Replace("(Join-Path `$PSScriptRoot 'Test-RatRaceLegacyRelease.ps1')", ("'" + $helper.Replace("'","''") + "'"))
    $code = $code.Replace('G:\RatRace_StagingSecured',"$temporary\destination").Replace('G:\RatRace_StagingBackup',"$temporary\backup").Replace('G:\RatRace_Staging',$source)
    $script = [scriptblock]::Create($code)
    function Get-CimInstance { @() }
    function Get-NetTCPConnection { @() }
    $report = & $script -Mode DryRun -CurrentCommit $commit -CurrentReleaseRelative $relativeRelease -ReviewedCheckout $checkout | ConvertFrom-Json
    if ($report.files -lt 4 -or (Test-Path "$temporary\destination") -or (Test-Path "$temporary\backup")) { throw 'Dry run mutated destination or missed inventory.' }
    foreach ($relative in @('..\production','C:\GSA','releases\..\..\outside')) {
        $rejected = $false
        try { & $script -CurrentCommit $commit -CurrentReleaseRelative $relative -ReviewedCheckout $checkout | Out-Null } catch { $rejected = $true }
        if (-not $rejected) { throw 'Migration accepted an arbitrary path.' }
    }
    [IO.File]::WriteAllText("$source\pgdata\postmaster.pid",'1')
    $rejected = $false
    try { & $script -CurrentCommit $commit -CurrentReleaseRelative $relativeRelease -ReviewedCheckout $checkout | Out-Null } catch { $rejected = $_.Exception.Message -match 'cleanly stopped' }
    if (-not $rejected) { throw 'Live cluster was accepted.' }
    [IO.File]::Delete("$source\pgdata\postmaster.pid")
    [IO.File]::WriteAllText("$source\config\staging.env", $environment.Replace('5433','5432'))
    $rejected = $false
    try { & $script -CurrentCommit $commit -CurrentReleaseRelative $relativeRelease -ReviewedCheckout $checkout | Out-Null } catch { $rejected = $_.Exception.Message -match '5433' }
    if (-not $rejected) { throw 'Production database port was accepted.' }
    . $helper
    foreach ($mutation in @('changed','missing','extra')) {
        $file = "$legacy\apps\website\manage.py"
        if ($mutation -eq 'changed') { [IO.File]::WriteAllText($file,'changed') }
        if ($mutation -eq 'missing') { [IO.File]::Delete($file) }
        if ($mutation -eq 'extra') { [IO.File]::WriteAllText("$legacy\extra.txt",'extra') }
        $rejected = $false
        try { Test-RatRaceLegacyRelease $legacy $commit $checkout | Out-Null } catch { $rejected = $true }
        if (-not $rejected) { throw "Accepted $mutation legacy archive." }
        [IO.File]::WriteAllText($file,'# fixture')
        if (Test-Path "$legacy\extra.txt") { [IO.File]::Delete("$legacy\extra.txt") }
    }
    Test-RatRaceLegacyRelease $legacy $commit $checkout | Out-Null
    if ((Test-Path "$legacy\staging-release.json") -or (Test-Path "$legacy\.git")) { throw 'Verifier changed source release.' }
    & git -C $checkout update-ref -d refs/remotes/origin/codex/rat-race-dev
    $rejected = $false
    try { Test-RatRaceLegacyRelease $legacy $commit $checkout | Out-Null } catch { $rejected = $true }
    if (-not $rejected) { throw 'Accepted unproven branch ancestry.' }
    Write-Output 'Migration preflight and dry-run fixtures passed.'
} finally {
    $resolved = [IO.Path]::GetFullPath($temporary)
    if (-not $resolved.StartsWith([IO.Path]::GetFullPath([IO.Path]::GetTempPath()),[StringComparison]::OrdinalIgnoreCase) -or [IO.Path]::GetFileName($resolved) -notlike 'staging-preflight-*') { throw 'Unsafe fixture cleanup path.' }
    Remove-Item -LiteralPath $resolved -Recurse -Force
}
