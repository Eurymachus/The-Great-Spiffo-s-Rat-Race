param([ValidateSet('Preview','Check')][string]$Mode='Check')
$ErrorActionPreference='Stop'
$root='G:\RatRace_Staging'
$state="$root\retention-preview-operations"
$name='RatRaceStagingRetentionPreview'
. "$PSScriptRoot\RatRaceStagingRetentionPreviewHelpers.ps1"
$phase='preflight'
$results=[ordered]@{}
$locks=@()
$report=$false
try {
    Assert-PreviewBundle $state $PSScriptRoot
    $report=$true
    foreach($task in $name,($name+'Check')){
        if(!(Get-ScheduledTask -TaskName $task).Settings.Enabled){throw 'Task disabled'}
    }
    if($Mode -eq 'Check'){
        $phase='freshness'
        $path="$state\Preview.json"
        Assert-NoRedirect $path
        $record=Get-Content -LiteralPath $path -Raw | ConvertFrom-Json
        $task=Get-ScheduledTask -TaskName $name
        $info=Get-ScheduledTaskInfo -TaskName $name
        Assert-FreshPreview $record $task.State $info.LastTaskResult ([DateTimeOffset]::UtcNow)
    }else{
        $phase='coordination'
        $locks+=Acquire-PreviewLock 'Global\RatRaceStagingRetentionPreview'
        Write-PreviewState "$state\Preview.json" 'running' $phase $results
        $locks+=Acquire-PreviewLock 'Global\RatRaceStagingBackup'
        $phase='release'
        $config="$root\config\staging.env"
        Assert-NoRedirect $config
        Assert-PreviewAcl $config
        $line=@(Get-Content -LiteralPath $config | Where-Object {$_ -match '^RELEASE_ID='})
        if($line.Count -ne 1 -or $line[0] -notmatch '^RELEASE_ID=([a-f0-9]{7,40})$'){throw 'Invalid release'}
        $release=$Matches[1]
        $releasePath="$root\releases\$release"
        foreach($service in 'RatRaceStagingWeb','RatRaceStagingWorker'){
            $task=Get-ScheduledTask -TaskName $service
            if(!$task.Settings.Enabled -or $task.State -ne 'Running' -or $task.Actions.Count -ne 1 -or
                $task.Actions[0].Arguments -notmatch ('-ReleaseRoot\s+"'+[regex]::Escape($releasePath)+'"')){throw 'Release mismatch'}
        }
        $phase='previews'
        $python="$root\venv\Scripts\python.exe"
        $tool=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\scripts\staging_retention_preview.py'))
        Assert-NoRedirect $tool
        Assert-NoRedirect $python
        $output=& $python -B $tool $release 2>$null
        $code=$LASTEXITCODE
        $results=$output | ConvertFrom-Json
        if($code -ne 0 -or !$results){throw 'Preview failed or needs review'}
    }
    Write-PreviewState "$state\$Mode.json" 'success' 'verified' $results
} catch {
    if($report -and ($Mode -eq 'Check' -or $locks.Count)){
        try {Write-PreviewState "$state\$Mode.json" 'failed' $phase $results} catch {}
    }
    Write-EventLog -LogName Application -Source $name -EntryType Error -EventId 4201 -Message "Staging retention $Mode failed or needs review at $phase. See protected status."
    exit 1
} finally {
    foreach($lock in $locks){$lock.ReleaseMutex();$lock.Dispose()}
}
Write-EventLog -LogName Application -Source $name -EntryType Information -EventId 4200 -Message "Staging retention $Mode passed. See protected status."
exit 0
