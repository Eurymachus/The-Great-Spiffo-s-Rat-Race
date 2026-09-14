param([Parameter(Mandatory=$true)][ValidatePattern('^[0-9a-f]{40}$')][string]$Commit)
$ErrorActionPreference = 'Stop'
$root = 'G:\RatRace_StagingSecured'
function Read-DeploymentResult {
    $file = [IO.File]::Open("$root\control\result\status.json", 'Open', 'Read', ([IO.FileShare]::ReadWrite -bor [IO.FileShare]::Delete))
    $reader = New-Object IO.StreamReader($file)
    try { $reader.ReadToEnd() | ConvertFrom-Json } finally { $reader.Dispose() }
}
$status = Read-DeploymentResult
if ($status.status -eq 'running') {
    if ((Get-ScheduledTask -TaskName 'RatRaceStagingDeploy' -TaskPath '\').State -eq 'Running') { throw 'A deployment is already running.' }
    # Restart only to mark an interrupted request failed, never to replay it.
    Start-ScheduledTask -TaskName 'RatRaceStagingDeploy' -TaskPath '\'
    $recoveryDeadline = (Get-Date).AddSeconds(30)
    do {
        Start-Sleep -Seconds 1
        $status = Read-DeploymentResult
    } while ($status.status -eq 'running' -and (Get-Date) -lt $recoveryDeadline)
    throw 'Previous deployment was interrupted. Its result has been refreshed. Inspect it and the active release before submitting another deployment.'
}
$payload = @{schema=1; sequence=[long]$status.next_sequence; commit=$Commit} | ConvertTo-Json -Compress
# Existing administrator-owned file only. No creation, replacement or executable input.
$stream = New-Object IO.FileStream("$root\control\inbox\request.json", [IO.FileMode]::Open, [Security.AccessControl.FileSystemRights]::WriteData, [IO.FileShare]::None, 4096, [IO.FileOptions]::WriteThrough)
try {
    $bytes = [Text.Encoding]::UTF8.GetBytes($payload)
    $stream.Write($bytes, 0, $bytes.Length)
    $stream.SetLength($bytes.Length)
    $stream.Flush($true)
} finally { $stream.Dispose() }
try { Start-ScheduledTask -TaskName 'RatRaceStagingDeploy' -TaskPath '\' }
catch { throw 'Cannot start the fixed deployment task. Administrator must repair its operator Read/Execute ACL; do not grant task-definition write access.' }
$deadline = (Get-Date).AddMinutes(30)
do {
    Start-Sleep -Seconds 2
    $result = Read-DeploymentResult
    if ($result.sequence -eq $status.next_sequence -and $result.status -ne 'running') {
        $result | ConvertTo-Json -Depth 5
        if ($result.status -ne 'succeeded') { throw 'Staging deployment failed. See reported status.' }
        return
    }
} while ((Get-Date) -lt $deadline)
throw 'Timed out waiting for this request. Read control\result\status.json before retrying.'
