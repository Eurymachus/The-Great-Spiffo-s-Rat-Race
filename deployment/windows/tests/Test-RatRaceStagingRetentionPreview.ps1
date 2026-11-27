param([Parameter(Mandatory=$true)][string]$FixtureRoot)
$ErrorActionPreference='Stop'
. "$PSScriptRoot\..\RatRaceStagingRetentionPreviewHelpers.ps1"
Assert-NoRedirect $FixtureRoot
foreach($case in @(
    @('2026-11-27T11:44:59','2026-11-27T11:45:00'),
    @('2026-11-27T11:45:00','2026-11-27T12:45:00'),
    @('2026-11-27T11:46:00','2026-11-27T12:45:00'),
    @('2026-12-31T23:55:00','2027-01-01T00:45:00')
)){
    if((Get-NextPreviewCheck ([datetime]$case[0])) -ne [datetime]$case[1]){throw 'Schedule case failed'}
}
$now=[DateTimeOffset]::Parse('2026-11-27T12:00:00Z')
foreach($case in @(
    @('success','Ready',0,-29,$true),
    @('success','Ready',0,-31,$false),
    @('success','Ready',0,1,$false),
    @('running','Ready',0,-1,$false),
    @('success','Running',0,-1,$false),
    @('failed','Ready',1,-1,$false),
    @('success','Disabled',0,-1,$false)
)){
    $record=@{state=$case[0];checked_at=$now.AddHours($case[3]).ToString('o')}
    $passed=$true
    try{Assert-FreshPreview $record $case[1] $case[2] $now}catch{$passed=$false}
    if($passed -ne $case[4]){throw 'Monitor case failed'}
}
$path=Join-Path $FixtureRoot ('status-'+[Guid]::NewGuid().ToString('N')+'.json')
Write-PreviewState $path 'running' 'synthetic' $null
Write-PreviewState $path 'success' 'synthetic' @{count=0}
if((Get-Content -LiteralPath $path -Raw|ConvertFrom-Json).state -ne 'success'){throw 'Atomic status replacement failed'}
'4 cadence cases, 7 monitor cases and atomic status replacement passed.'
