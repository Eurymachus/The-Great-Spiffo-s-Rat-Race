function Test-RatRaceLegacyRelease {
    param([Parameter(Mandatory=$true)][string]$Release,
          [Parameter(Mandatory=$true)][string]$Commit,
          [Parameter(Mandatory=$true)][string]$ReviewedCheckout)
    $ErrorActionPreference = 'Stop'
    if ($Commit -cnotmatch '^[0-9a-f]{40}$') { throw 'Exact full commit required.' }
    $name = [IO.Path]::GetFileName($Release.TrimEnd('\'))
    if ($name -cnotmatch '^[0-9a-f]{7,40}$' -or -not $Commit.StartsWith($name)) { throw 'Release directory must identify the exact commit.' }
    $git = @('-c','core.fsmonitor=false','-c','core.hooksPath=NUL','-C',$ReviewedCheckout)
    $dirty = & git @git status --porcelain --untracked-files=all
    if ($LASTEXITCODE -or $dirty) { throw 'A reviewed clean checkout is required.' }
    $resolved = & git @git rev-parse --verify "$Commit`^{commit}"
    if ($LASTEXITCODE -or $resolved -cne $Commit) { throw 'Commit identity is ambiguous or unavailable.' }
    & git @git merge-base --is-ancestor $Commit refs/remotes/origin/codex/rat-race-dev
    if ($LASTEXITCODE) { throw 'Commit is not in origin/codex/rat-race-dev.' }
    $temporary = Join-Path ([IO.Path]::GetTempPath()) ('staging-archive-' + [guid]::NewGuid().ToString('N') + '.zip')
    try {
        & git @git archive --format=zip "--output=$temporary" $Commit
        if ($LASTEXITCODE) { throw 'Cannot create verification archive.' }
        Add-Type -AssemblyName System.IO.Compression.FileSystem
        $archive = [IO.Compression.ZipFile]::OpenRead($temporary)
        $hashes = @{}
        try {
            foreach ($entry in $archive.Entries) {
                $relative = $entry.FullName
                if ($relative.EndsWith('/')) { continue }
                if ($relative -match '(^/|\\|:|(^|/)\.\.(/|$))' -or $relative -eq 'staging-release.json' -or $hashes.ContainsKey($relative) -or (($entry.ExternalAttributes -shr 16) -band 61440) -eq 40960) { throw 'Unsafe or duplicate archive entry.' }
                $stream = $entry.Open()
                $sha = [Security.Cryptography.SHA256]::Create()
                try { $hashes[$relative] = ([BitConverter]::ToString($sha.ComputeHash($stream))).Replace('-','').ToLowerInvariant() }
                finally { $stream.Dispose(); $sha.Dispose() }
            }
        } finally { $archive.Dispose() }
        foreach ($required in @('apps/website/manage.py','apps/website/config/asgi.py','apps/website/config/settings_windows_staging.py')) {
            if (-not $hashes.ContainsKey($required)) { throw 'Incomplete website archive.' }
        }
        $actual = @{}
        foreach ($item in Get-ChildItem -LiteralPath $Release -Force -Recurse) {
            if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Reparse point in release.' }
            if ($item.PSIsContainer) { continue }
            $relative = $item.FullName.Substring($Release.TrimEnd('\').Length + 1).Replace('\','/')
            if ($relative -ceq 'staging-release.json') { continue }
            $actual[$relative] = (Get-FileHash -LiteralPath $item.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
        }
        if ($actual.Count -ne $hashes.Count) { throw 'Legacy release file inventory differs from Git archive.' }
        foreach ($relative in $hashes.Keys) {
            if (@($actual.Keys) -cnotcontains $relative -or $actual[$relative] -cne $hashes[$relative]) { throw 'Legacy release missing or changed file.' }
        }
        $existing = Join-Path $Release 'staging-release.json'
        if (Test-Path -LiteralPath $existing) {
            $manifest = Get-Content -LiteralPath $existing -Raw | ConvertFrom-Json
            if ($manifest.schema -ne 1 -or $manifest.commit -cne $Commit -or @($manifest.files.PSObject.Properties).Count -ne $hashes.Count) { throw 'Existing manifest mismatch.' }
            foreach ($entry in $manifest.files.PSObject.Properties) {
                if (-not $hashes.ContainsKey($entry.Name) -or $hashes[$entry.Name] -cne $entry.Value) { throw 'Existing manifest hash mismatch.' }
            }
        }
        return @{schema=1; commit=$Commit; files=$hashes}
    } finally {
        # Only the exact generated archive is removed, never any release content.
        if (Test-Path -LiteralPath $temporary) { [IO.File]::Delete($temporary) }
    }
}
