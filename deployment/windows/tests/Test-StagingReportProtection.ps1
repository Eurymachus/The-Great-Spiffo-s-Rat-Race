$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\Staging-IsolationAudit.ps1')
function Check-Descriptor([string]$Role,[string]$Ace,[bool]$Safe,[string]$Owner='BA') {
    $descriptor = New-Object StagingIsolationNative+Descriptor
    $descriptor.Path='fixture'; $descriptor.Sddl="O:${Owner}G:BAD:P(A;;FA;;;BA)(A;;FA;;;SY)$Ace"
    $findings = [StagingIsolationNative]::EvaluateReportBoundary($descriptor,$Role)
    if (($findings.Count -eq 0) -ne $Safe) { throw "Unexpected boundary decision: $Role $Ace owner=$Owner" }
}
# Protected report/directory below a volume permitting unrelated sibling creation.
Check-Descriptor File '' $true
Check-Descriptor Directory '' $true
Check-Descriptor Ancestor '(A;;0x00000006;;;BU)' $true
foreach ($role in @('File','Directory','Ancestor')) {
    Check-Descriptor $role '(A;;FRFX;;;BU)' $true
    Check-Descriptor $role '(A;;SD;;;BU)' $false
    Check-Descriptor $role '(A;;WD;;;BU)' $false
    Check-Descriptor $role '(A;;WO;;;BU)' $false
    Check-Descriptor $role '(A;;GA;;;BU)' $false
    Check-Descriptor $role '' $false 'BU'
    Check-Descriptor $role '(A;OICIIO;FA;;;BU)' $true
}
Check-Descriptor Directory '(A;;0x00000040;;;BU)' $false
Check-Descriptor Ancestor '(A;;0x00000040;;;BU)' $false
foreach ($role in @('File','Directory')) {
    Check-Descriptor $role '(A;;0x00000006;;;BU)' $false
    Check-Descriptor $role '(A;;GW;;;BU)' $false
}
# Exercise the PowerShell walk's role selection, not only the native predicate.
$fixture = Join-Path ([IO.Path]::GetTempPath()) ('staging-boundary-' + [guid]::NewGuid().ToString('N'))
try {
    New-Item -ItemType Directory -Path "$fixture\parent\reports" -Force | Out-Null
    [IO.File]::WriteAllText("$fixture\parent\reports\audit.json",'{}')
    $body = (Get-Command Assert-StagingAuditProtection).ScriptBlock.ToString().Replace('[StagingIsolationNative]::Read($cursor.FullName,$true)','(Read-FixtureDescriptor $cursor.FullName)')
    function Read-FixtureDescriptor($Path) {
        $descriptor = New-Object StagingIsolationNative+Descriptor
        $descriptor.Path=$Path
        $ace = if ($Path -eq "$fixture\parent\reports" -or $Path -eq "$fixture\parent\reports\audit.json") { '' } else { '(A;;0x00000006;;;BU)' }
        if ($Path -eq $script:unsafePath) { $ace='(A;;0x00000040;;;BU)' }
        $descriptor.Sddl="O:BAG:BAD:P(A;;FA;;;BA)(A;;FA;;;SY)$ace"
        return $descriptor
    }
    $walk=[scriptblock]::Create($body)
    & $walk "$fixture\parent\reports\audit.json"
    & $walk "$fixture\parent\reports"
    $script:unsafePath="$fixture\parent"
    $rejected=$false
    try { & $walk "$fixture\parent\reports\audit.json" } catch { $rejected=$true }
    if (-not $rejected) { throw 'Parent DELETE_CHILD allowed removal of protected directory.' }
} finally {
    $resolved=[IO.Path]::GetFullPath($fixture)
    if (-not $resolved.StartsWith([IO.Path]::GetFullPath([IO.Path]::GetTempPath()),[StringComparison]::OrdinalIgnoreCase) -or [IO.Path]::GetFileName($resolved) -notlike 'staging-boundary-*') { throw 'Unsafe fixture cleanup.' }
    Remove-Item -LiteralPath $resolved -Recurse -Force
}
Write-Output 'Report file, directory and ancestor protection fixtures passed.'
