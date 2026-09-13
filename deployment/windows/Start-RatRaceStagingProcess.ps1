param([Parameter(Mandatory=$true)][ValidateSet('Web','Worker')][string]$Process)
$ErrorActionPreference = 'Stop'
$root = 'G:\RatRace\_Staging'
$python = Join-Path $root 'venv\Scripts\python.exe'
$launcher = Join-Path $root 'launchers\staging_release.py'
$log = Join-Path $root ('logs\' + $Process.ToLowerInvariant() + '.log')
# The task is Limited, under the dedicated local staging account, never SYSTEM.
$child = Start-Process -FilePath $python -ArgumentList @('-E', '-B', "`"$launcher`"", 'run', '--role', $Process) -WindowStyle Hidden -Wait -PassThru -RedirectStandardOutput $log -RedirectStandardError ([IO.Path]::ChangeExtension($log, '.error.log'))
# These are permanent services. Even an unexpected clean exit needs supervision.
if ($child.ExitCode -eq 0) { exit 1 }
exit $child.ExitCode
