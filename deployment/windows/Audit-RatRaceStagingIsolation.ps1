param([Parameter(Mandatory=$true)][string[]]$IsolationRoots,
      [string]$StagingAccount = "$env:COMPUTERNAME\RatRaceStage",
      [Parameter(Mandatory=$true)][string]$ReportPath)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'Staging-IsolationAudit.ps1')
$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Run the read-only audit as administrator, while staging remains online.' }
$parent = [IO.Path]::GetDirectoryName([IO.Path]::GetFullPath($ReportPath))
Assert-StagingAuditProtection $parent
if (Test-Path -LiteralPath $ReportPath) { throw 'Use a new report filename; previous reports are immutable.' }
$subjects = Get-StagingAuditSubjects $StagingAccount
$roots = Get-StagingIsolationRoots $IsolationRoots
$findings = @()
foreach ($isolationRoot in $roots) { if (-not [IO.Directory]::Exists($isolationRoot)) { $findings += "Missing or inaccessible directory root: $isolationRoot" } }
$boundaries = @()
try {
    $boundaries = Get-StagingIsolationBoundaries $roots
    foreach ($boundary in $boundaries) { $findings += [StagingIsolationNative]::Evaluate($boundary,@(),$true) }
} catch { $findings += $_.Exception.Message }
$scan = [StagingIsolationNative]::Scan($roots, @($subjects.sid) + $subjects.groups)
$findings += $scan.Findings
# Detect boundary replacement during the online scan.
try {
    $after = Get-StagingIsolationBoundaries $roots
    if (($after | ConvertTo-Json -Depth 6 -Compress) -cne ($boundaries | ConvertTo-Json -Depth 6 -Compress)) { $findings += 'Boundaries changed during audit.' }
} catch { $findings += $_.Exception.Message }
$report = @{schema=1; audited_at=[DateTimeOffset]::UtcNow.ToString('o'); roots=$roots; account_sid=$subjects.sid; group_sids=$subjects.groups; boundaries=$boundaries; descriptors=$scan.Descriptors; exceptional_paths=$scan.ExceptionalPaths; findings=@($findings); passed=($findings.Count -eq 0); metrics=@{entries=$scan.Entries; native_reads=$scan.NativeReads; descriptor_evaluations=$scan.Evaluations; exceptional_entries=$scan.ExceptionalEntries; powershell_get_acl_calls=0}}
$security = New-Object Security.AccessControl.FileSecurity
$security.SetAccessRuleProtection($true,$false)
$security.SetOwner((New-Object Security.Principal.SecurityIdentifier('S-1-5-32-544')))
foreach ($sid in @('S-1-5-18','S-1-5-32-544')) { $security.AddAccessRule((New-Object Security.AccessControl.FileSystemAccessRule((New-Object Security.Principal.SecurityIdentifier($sid)),'FullControl','Allow'))) }
$file = New-Object IO.FileStream($ReportPath,[IO.FileMode]::CreateNew,[Security.AccessControl.FileSystemRights]::FullControl,[IO.FileShare]::None,4096,[IO.FileOptions]::WriteThrough,$security)
try { $bytes=[Text.Encoding]::UTF8.GetBytes(($report | ConvertTo-Json -Depth 12)); $file.Write($bytes,0,$bytes.Length); $file.Flush($true) } finally { $file.Dispose() }
Write-Output "Isolation audit saved: $ReportPath; passed=$($report.passed); entries=$($scan.Entries); descriptor evaluations=$($scan.Evaluations)"
if (-not $report.passed) { throw 'Isolation audit requires review. No isolation permissions were changed.' }
