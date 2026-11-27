function Assert-NoRedirect([string]$Path){
    $path=[IO.Path]::GetFullPath($Path)
    while($path){
        $item=Get-Item -LiteralPath $path -Force -ErrorAction SilentlyContinue
        if($item -and ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)){throw 'Redirected path refused'}
        $path=[IO.Path]::GetDirectoryName($path)
    }
}
function Assert-PreviewAcl([string]$Path){
    $acl=Get-Acl -LiteralPath $Path
    $admin=(New-Object Security.Principal.NTAccount("$env:COMPUTERNAME\admin")).Translate([Security.Principal.SecurityIdentifier]).Value
    $trusted=@('S-1-5-18','S-1-5-32-544',$admin)
    $owner=$acl.GetOwner([Security.Principal.SecurityIdentifier]).Value
    $grants=@($acl.Access | Where-Object AccessControlType -eq Allow)
    if(!$acl.AreAccessRulesProtected -or $owner -notin $trusted -or !$grants.Count){throw 'Protected ACL required'}
    foreach($rule in $grants){
        if($rule.IdentityReference.Translate([Security.Principal.SecurityIdentifier]).Value -notin $trusted){throw 'Unexpected ACL principal'}
    }
}
function Assert-PreviewBundle([string]$State,[string]$ScriptRoot){
    $bundle=Split-Path -Parent (Split-Path -Parent $ScriptRoot)
    if((Split-Path -Parent $bundle) -ine $State -or (Split-Path -Leaf $bundle) -notmatch '^[a-f0-9]{8}$'){throw 'Not a versioned staging bundle'}
    Assert-NoRedirect $ScriptRoot
    Assert-PreviewAcl $State
    Assert-PreviewAcl $bundle
}
function Acquire-PreviewLock([string]$Name){
    $mutex=New-Object Threading.Mutex($false,$Name)
    try{
        if($mutex.WaitOne(0)){return $mutex}
        throw 'An operation is active'
    }catch{$mutex.Dispose();throw}
}
function Write-PreviewState([string]$Path,[string]$State,[string]$Stage,$Results){
    Assert-NoRedirect $Path
    $tmp=$Path+'.'+[Guid]::NewGuid().ToString('N')+'.tmp'
    $json=@{state=$State;stage=$Stage;checked_at=[DateTimeOffset]::UtcNow.ToString('o');results=$Results}|ConvertTo-Json -Depth 6
    [IO.File]::WriteAllText($tmp,$json,[Text.UTF8Encoding]::new($false))
    if([IO.File]::Exists($Path)){[IO.File]::Replace($tmp,$Path,[NullString]::Value)}
    else{[IO.File]::Move($tmp,$Path)}
}
function Assert-FreshPreview($Record,[string]$TaskState,[uint32]$LastResult,[DateTimeOffset]$Now){
    if($TaskState -ne 'Ready' -or $LastResult -ne 0 -or $Record.state -ne 'success'){throw 'Preview failed or interrupted'}
    $stamp=[DateTimeOffset]::Parse($Record.checked_at)
    if($stamp -gt $Now -or $stamp -lt $Now.AddHours(-30)){throw 'Preview timestamp invalid or stale'}
}
function Get-NextPreviewCheck([datetime]$Now){
    $next=$Now.Date.AddHours($Now.Hour).AddMinutes(45)
    if($next -le $Now){$next=$next.AddHours(1)}
    return $next
}
