param()
$ErrorActionPreference='Stop'
$state='G:\RatRace_Staging\retention-preview-operations'
. "$PSScriptRoot\RatRaceStagingRetentionPreviewHelpers.ps1"
Assert-PreviewBundle $state $PSScriptRoot
$runner="$PSScriptRoot\Run-RatRaceStagingRetentionPreview.ps1"
Assert-NoRedirect $runner
$name='RatRaceStagingRetentionPreview'
if(![Diagnostics.EventLog]::SourceExists($name)){New-EventLog -LogName Application -Source $name}
$principal=New-ScheduledTaskPrincipal -UserId SYSTEM -LogonType ServiceAccount -RunLevel Highest
$settings=New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 20)
$daily=New-ScheduledTaskTrigger -Daily -At '05:00'
$hourly=New-ScheduledTaskTrigger -Once -At (Get-NextPreviewCheck (Get-Date)) -RepetitionInterval (New-TimeSpan -Hours 1)
foreach($spec in @(@($name,'Preview',$daily),@(($name+'Check'),'Check',$hourly))){
    $arguments='-NoProfile -ExecutionPolicy Bypass -File "{0}" -Mode {1}' -f $runner,$spec[1]
    $action=New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $arguments
    Register-ScheduledTask -TaskName $spec[0] -Action $action -Trigger $spec[2] -Principal $principal -Settings $settings -Description 'Staging-only retention preview or local failure check.' -Force|Out-Null
}
