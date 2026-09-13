$ErrorActionPreference = 'Stop'
$temporary = Join-Path ([IO.Path]::GetTempPath()) ('staging-submit-' + [guid]::NewGuid().ToString('N'))
try {
    New-Item -ItemType Directory -Path "$temporary\control\inbox","$temporary\control\result" -Force | Out-Null
    [IO.File]::WriteAllText("$temporary\control\inbox\request.json", '{}')
    [IO.File]::WriteAllText("$temporary\control\result\status.json", '{"schema":1,"sequence":0,"next_sequence":1,"status":"idle"}')
    function Start-ScheduledTask {
        param($TaskName,$TaskPath)
        if ($TaskName -cne 'RatRaceStagingDeploy' -or $TaskPath -cne '\') { throw 'Client selected another task.' }
        $request = Get-Content "$temporary\control\inbox\request.json" -Raw | ConvertFrom-Json
        if ($request.commit -cne ('a'*40) -or $request.sequence -ne 1) { throw 'Client request mismatch.' }
        if ($request.request_id -cnotmatch '^[0-9a-f]{32}$') { throw 'Missing random request ID.' }
        $reply = @{schema=1;sequence=1;next_sequence=2;status='succeeded';commit=$request.commit;request_id=$request.request_id}
        if ($scenario -eq 'commit') { $reply.commit = 'b'*40 }
        if ($scenario -eq 'nonce') { $reply.request_id = '0'*32 }
        if ($scenario -eq 'newer') { $reply.sequence = 2 }
        [IO.File]::WriteAllText("$temporary\control\result\status.json", ($reply | ConvertTo-Json -Compress))
    }
    function Start-Sleep { param($Seconds) }
    $code = [IO.File]::ReadAllText((Join-Path $PSScriptRoot '..\Submit-RatRaceStagingDeployment.ps1')).Replace('G:\RatRace_StagingSecured',$temporary)
    $result = & ([scriptblock]::Create($code)) -Commit ('a'*40) | ConvertFrom-Json
    if ($result.status -ne 'succeeded') { throw 'Client did not return the matching result.' }
    foreach ($scenario in @('commit','nonce','newer')) {
        [IO.File]::WriteAllText("$temporary\control\result\status.json", '{"schema":1,"sequence":0,"next_sequence":1,"status":"idle"}')
        $rejected = $false
        $output = @()
        try { $output = @(& ([scriptblock]::Create($code)) -Commit ('a'*40)) } catch { $rejected = $_.Exception.Message -match 'superseded' }
        if (-not $rejected -or $output.Count) { throw "Client falsely confirmed a $scenario mismatch." }
    }
    # Validate SID-based ACL construction without applying host permissions.
    $acl = New-Object Security.AccessControl.FileSecurity
    $sid = New-Object Security.Principal.SecurityIdentifier('S-1-5-32-545')
    $acl.AddAccessRule((New-Object Security.AccessControl.FileSystemAccessRule($sid, 'Read,WriteData,Synchronize','Allow')))
    $rights = $acl.GetAccessRules($true,$false,[Security.Principal.SecurityIdentifier])[0].FileSystemRights
    if ($rights -band [Security.AccessControl.FileSystemRights]'Delete,ChangePermissions,TakeOwnership') { throw 'Request ACL grants excessive rights.' }
    Write-Output 'Operator submission and narrow ACL construction fixtures passed.'
} finally {
    $resolved = [IO.Path]::GetFullPath($temporary)
    if (-not $resolved.StartsWith([IO.Path]::GetFullPath([IO.Path]::GetTempPath()),[StringComparison]::OrdinalIgnoreCase) -or [IO.Path]::GetFileName($resolved) -notlike 'staging-submit-*') { throw 'Unsafe fixture cleanup path.' }
    Remove-Item -LiteralPath $resolved -Recurse -Force
}
