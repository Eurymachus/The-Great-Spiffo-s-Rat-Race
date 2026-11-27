param()
$ErrorActionPreference = 'Stop'
$root = 'G:\RatRace_Staging'
$stateRoot = Join-Path $root 'backup-operations'
$runner = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot 'Run-RatRaceStagingBackup.ps1')).Path
if (-not $runner.StartsWith($stateRoot + '\', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Install from the protected, versioned staging backup-operations bundle.'
}
if (-not [Diagnostics.EventLog]::SourceExists('RatRaceStagingBackup')) {
    New-EventLog -LogName Application -Source 'RatRaceStagingBackup'
}
$principal = New-ScheduledTaskPrincipal -UserId SYSTEM -LogonType ServiceAccount -RunLevel Highest
# No execution limit: killing the coordinator could bypass its restart finally block.
# The independent hourly check flags a stuck/interrupted run.
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit ([TimeSpan]::Zero)
$daily = New-ScheduledTaskTrigger -Daily -At '04:00'
$now = Get-Date
$nextCheck = $now.Date.AddHours($now.Hour).AddMinutes(15)
if ($nextCheck -le $now) {
    $nextCheck = $nextCheck.AddHours(1)
}
$hourly = New-ScheduledTaskTrigger -Once -At $nextCheck -RepetitionInterval (New-TimeSpan -Hours 1)
foreach ($spec in @(@('RatRaceStagingBackup','Capture',$daily), @('RatRaceStagingBackupCheck','Check',$hourly))) {
    $action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$runner`" -Mode $($spec[1])"
    Register-ScheduledTask -TaskName $spec[0] -Action $action -Trigger $spec[2] -Principal $principal -Settings $settings -Description 'Staging-only local backup or integrity/freshness check. No retention deletion.' -Force | Out-Null
}
