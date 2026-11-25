param([Parameter(Mandatory = $true)][string]$Path)
$ErrorActionPreference = 'Stop'
$item = Get-Item -LiteralPath $Path -Force
if (-not $item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
    throw 'Artifact root must be a real directory.'
}
$identity = [Security.Principal.WindowsIdentity]::GetCurrent().User
$acl = New-Object Security.AccessControl.DirectorySecurity
$acl.SetAccessRuleProtection($true, $false)
$acl.SetOwner($identity)
foreach ($sid in @('S-1-5-18', 'S-1-5-32-544', $identity.Value) | Select-Object -Unique) {
    $rule = New-Object Security.AccessControl.FileSystemAccessRule(
        (New-Object Security.Principal.SecurityIdentifier($sid)), 'FullControl',
        'ContainerInherit,ObjectInherit', 'None', 'Allow')
    $acl.AddAccessRule($rule)
}
Set-Acl -LiteralPath $item.FullName -AclObject $acl
$verified = Get-Acl -LiteralPath $item.FullName
if (-not $verified.AreAccessRulesProtected) { throw 'Artifact ACL inheritance remains enabled.' }
foreach ($rule in $verified.Access) {
    $sid = $rule.IdentityReference.Translate([Security.Principal.SecurityIdentifier]).Value
    if ($sid -notin @('S-1-5-18', 'S-1-5-32-544', $identity.Value)) {
        throw 'Unexpected artifact ACL principal.'
    }
}
