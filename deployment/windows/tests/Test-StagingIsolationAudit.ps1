$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\Staging-IsolationAudit.ps1')
$temporary = Join-Path ([IO.Path]::GetTempPath()) ('staging-isolation-' + [guid]::NewGuid().ToString('N'))
try {
    New-Item -ItemType Directory -Path $temporary | Out-Null
    foreach ($n in 1..20) {
        $directory = Join-Path $temporary "d$n"
        New-Item -ItemType Directory -Path $directory | Out-Null
        foreach ($file in 1..100) { [IO.File]::WriteAllText((Join-Path $directory "f$file"),'fixture') }
    }
    function Get-Acl { throw 'Audit must not invoke Get-Acl per file.' }
    $scan = [StagingIsolationNative]::Scan(@($temporary),@('S-1-5-21-1-2-3-9999'))
    if ($scan.Entries -ne 2021 -or $scan.NativeReads -ne 2021 -or $scan.Evaluations -gt 10) { throw "Descriptor cache regression: $($scan.Evaluations) evaluations / $($scan.Entries) entries" }
    if ($scan.Findings.Count) { throw ($scan.Findings -join '; ') }
    $exceptionPath=Join-Path $temporary 'd1\f1'
    $fileAcl=[IO.File]::GetAccessControl($exceptionPath)
    $fileAcl.SetAccessRuleProtection($true,$false)
    $fileAcl.AddAccessRule((New-Object Security.AccessControl.FileSystemAccessRule([Security.Principal.WindowsIdentity]::GetCurrent().User,'FullControl','Allow')))
    $fileAcl.AddAccessRule((New-Object Security.AccessControl.FileSystemAccessRule((New-Object Security.Principal.SecurityIdentifier('S-1-1-0')),'Read','Allow')))
    [IO.File]::SetAccessControl($exceptionPath,$fileAcl)
    $exceptionScan=[StagingIsolationNative]::Scan(@($temporary),@('S-1-1-0'))
    if (-not @($exceptionScan.Findings | Where-Object { $_.Contains($exceptionPath) }).Count -or $exceptionScan.Evaluations -gt 11) { throw 'Protected explicit exception was missed or not cached.' }
    $missing = [StagingIsolationNative]::Scan(@("$temporary\missing"),@())
    if (-not $missing.Findings.Count) { throw 'Inaccessible/missing path passed.' }
    $descriptor = [StagingIsolationNative]::Read($temporary,$true)
    if (-not $descriptor.Identity -or $descriptor.Hash.Length -ne 64) { throw 'Missing identity/hash.' }
    $unsafe = New-Object StagingIsolationNative+Descriptor
    $unsafe.Path='fixture'; $unsafe.Owner='S-1-5-18'; $unsafe.Sddl='O:SYG:SYD:P(A;;FA;;;WD)'
    if (-not [StagingIsolationNative]::Evaluate($unsafe,@('S-1-1-0'),$false).Count) { throw 'Explicit unsafe descriptor passed.' }
    $installer = Get-Content (Join-Path $PSScriptRoot '..\Install-RatRaceStagingStartup.ps1') -Raw
    if ($installer -match 'Get-ChildItem' -or $installer -notmatch 'Assert-StagingIsolationReport') { throw 'Installer must use bounded report validation.' }
    # Validate the real report gate with only host identity/protection adapters mocked.
    function Assert-StagingAuditProtection { param($Path) if ($script:unprotected) { throw 'Unprotected report' } }
    function Get-StagingAuditSubjects { param($Account) @{sid='fixture';groups=@('group')} }
    function Get-StagingIsolationRoots { param($Roots) @('fixture-root') }
    function Get-StagingIsolationBoundaries { param($Roots) @($descriptor) }
    $reportPath = Join-Path $temporary 'report.json'
    $report = @{schema=1;audited_at=[DateTimeOffset]::UtcNow.ToString('o');roots=@('fixture-root');account_sid='fixture';group_sids=@('group');boundaries=@($descriptor);descriptors=@($descriptor);exceptional_paths=@();findings=@();passed=$true;metrics=@{}}
    $valid = $report | ConvertTo-Json -Depth 10
    [IO.File]::WriteAllText($reportPath,$valid)
    Assert-StagingIsolationReport $reportPath @('fixture-root') 'fixture'
    foreach ($failure in @('stale','account','roots','groups','boundary','failed','schema','unprotected')) {
        $changed = $valid | ConvertFrom-Json
        $script:unprotected = $false
        switch ($failure) {
            stale { $changed.audited_at=[DateTimeOffset]::UtcNow.AddHours(-5).ToString('o') }
            account { $changed.account_sid='other' }
            roots { $changed.roots=@('other') }
            groups { $changed.group_sids=@('other') }
            boundary { $changed.boundaries[0].Hash='changed' }
            failed { $changed.passed=$false }
            schema { $changed.schema=2 }
            unprotected { $script:unprotected=$true }
        }
        [IO.File]::WriteAllText($reportPath,($changed | ConvertTo-Json -Depth 10))
        $rejected=$false
        try { Assert-StagingIsolationReport $reportPath @('fixture-root') 'fixture' } catch { $rejected=$true }
        if (-not $rejected) { throw "Report gate accepted $failure." }
    }
    Write-Output "Isolation audit fixture passed: $($scan.Entries) entries, $($scan.Evaluations) descriptor evaluations, zero Get-Acl calls."
} finally {
    $resolved=[IO.Path]::GetFullPath($temporary)
    if (-not $resolved.StartsWith([IO.Path]::GetFullPath([IO.Path]::GetTempPath()),[StringComparison]::OrdinalIgnoreCase) -or [IO.Path]::GetFileName($resolved) -notlike 'staging-isolation-*') { throw 'Unsafe fixture cleanup.' }
    Remove-Item -LiteralPath $resolved -Recurse -Force
}
