$ErrorActionPreference = 'Stop'
if (-not ('StagingIsolationNative' -as [type])) { Add-Type -Path (Join-Path $PSScriptRoot 'StagingIsolationNative.cs') }
function Get-StagingAuditSubjects([string]$Account) {
    $sid = (New-Object Security.Principal.NTAccount($Account)).Translate([Security.Principal.SecurityIdentifier]).Value
    $subjects = @($sid,'S-1-1-0','S-1-2-0','S-1-5-11','S-1-5-32-545','S-1-5-3','S-1-5-113')
    $groups = @(Get-LocalGroup | ForEach-Object { @{sid=$_.SID.Value; members=@(Get-LocalGroupMember -Group $_ -ErrorAction Stop).SID.Value} })
    do {
        $before = $subjects.Count
        foreach ($group in $groups) { if (@($group.members | Where-Object { $_ -in $subjects }).Count -and $group.sid -notin $subjects) { $subjects += $group.sid } }
    } while ($before -ne $subjects.Count)
    if ('S-1-5-32-544' -in $subjects) { throw 'Staging account must not be an administrator.' }
    @{sid=$sid; groups=@($subjects | Where-Object { $_ -ne $sid } | Sort-Object -Unique)}
}
function Get-StagingIsolationRoots([string[]]$Roots) {
    if ($Roots.Count -lt 2) { throw 'Inventory production and GSA roots.' }
    @($Roots | ForEach-Object {
        if (-not [IO.Path]::IsPathRooted($_)) { throw 'Absolute isolation roots required.' }
        $full = [IO.Path]::GetFullPath($_)
        $path = if ($full -ieq [IO.Path]::GetPathRoot($full)) { $full } else { $full.TrimEnd('\') }
        $path
    } | Sort-Object -Unique)
}
function Get-StagingIsolationBoundaries([string[]]$Roots) {
    $paths = @{}
    foreach ($rootPath in $Roots) {
        $cursor = [IO.DirectoryInfo]$rootPath
        while ($cursor) { $paths[$cursor.FullName] = $true; $cursor = $cursor.Parent }
    }
    @($paths.Keys | Sort-Object | ForEach-Object { [StagingIsolationNative]::Read($_,$true) })
}
function Assert-StagingAuditProtection([string]$Path) {
    $cursor = Get-Item -LiteralPath $Path
    # The audit producer passes its existing output directory; the installer
    # passes the report file. Both must identify the same immediate boundary.
    $role = if ($cursor -is [IO.FileInfo]) { 'File' } else { 'Directory' }
    while ($cursor) {
        $descriptor = [StagingIsolationNative]::Read($cursor.FullName,$true)
        $issues = [StagingIsolationNative]::EvaluateReportBoundary($descriptor,$role)
        if ($issues.Count) { throw ($issues -join '; ') }
        $cursor = if ($cursor -is [IO.FileInfo]) { $cursor.Directory } else { $cursor.Parent }
        $role = if ($role -eq 'File') { 'Directory' } else { 'Ancestor' }
    }
}
function Assert-StagingIsolationReport([string]$Report, [string[]]$Roots, [string]$Account) {
    Assert-StagingAuditProtection $Report
    $value = Get-Content -LiteralPath $Report -Raw | ConvertFrom-Json
    $expected = @('schema','audited_at','roots','account_sid','group_sids','boundaries','descriptors','exceptional_paths','findings','passed','metrics')
    if ($value.schema -isnot [int] -or $value.schema -ne 1 -or ((@($value.PSObject.Properties.Name | Sort-Object) -join ',') -cne (($expected | Sort-Object) -join ','))) { throw 'Invalid isolation report schema.' }
    $stamp = [DateTimeOffset]::Parse($value.audited_at)
    $age = [DateTimeOffset]::UtcNow - $stamp
    if ($age.TotalHours -gt 4 -or $age.TotalMinutes -lt -5 -or $value.passed -isnot [bool] -or $value.passed -ne $true -or @($value.findings).Count) { throw 'Isolation report failed or is stale (maximum four hours).' }
    $subjects = Get-StagingAuditSubjects $Account
    $canonical = Get-StagingIsolationRoots $Roots
    if (($canonical -join '|') -ine (@($value.roots) -join '|') -or $subjects.sid -cne $value.account_sid -or ($subjects.groups -join '|') -cne (@($value.group_sids) -join '|')) { throw 'Isolation report roots/account/groups differ.' }
    $boundaries = Get-StagingIsolationBoundaries $canonical
    if ($boundaries.Count -ne @($value.boundaries).Count) { throw 'Isolation boundary inventory changed.' }
    foreach ($boundary in $boundaries) {
        $saved = @($value.boundaries | Where-Object Path -ieq $boundary.Path)
        if ($saved.Count -ne 1 -or $saved[0].Hash -cne $boundary.Hash -or $saved[0].Identity -cne $boundary.Identity) { throw 'Isolation boundary identity or descriptor changed; audit again.' }
    }
}
