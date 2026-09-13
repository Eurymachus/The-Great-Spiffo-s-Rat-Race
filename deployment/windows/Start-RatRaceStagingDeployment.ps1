$ErrorActionPreference = 'Stop'
$root = 'G:\RatRace_StagingSecured'
$child = Start-Process -FilePath "$root\venv\Scripts\python.exe" -ArgumentList @('-I', '-B', "`"$root\launchers\staging_control_entry.py`"") -WindowStyle Hidden -Wait -PassThru -RedirectStandardOutput "$root\logs\deployment.log" -RedirectStandardError "$root\logs\deployment.error.log"
exit $child.ExitCode
