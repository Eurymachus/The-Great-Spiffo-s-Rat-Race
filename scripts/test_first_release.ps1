param([ValidateRange(0, 2)][int]$Verbosity = 1, [switch]$PostgreSQL)

$ErrorActionPreference = "Stop"
$workspaceRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $workspaceRoot ".venv\Scripts\python.exe"
$managePath = Join-Path $workspaceRoot "apps\website\manage.py"
$testModules = @(
    "config", "registry.tests", "registry.test_mods", "registry.test_first_release",
    "registry.test_retention", "registry.test_closure_redaction", "registry.test_evidence_retention",
    "registry.test_legacy_concurrency", "registry.test_legacy_rehearsal", "registry.test_submission_policy",
    "pages", "operations.test_leaderboard_publish", "operations.test_deployment_checks",
    "operations.test_launch_maintenance", "operations.test_runtime_state",
    "registry.test_run_exports.RunSubmissionTests", "registry.test_leaderboard"
)
# settings_test uses disposable SQLite test storage. It does not load a host
# environment file or migrate the existing development database.
$settings = if ($PostgreSQL) { 'config.settings_test_postgresql' } else { 'config.settings_test' }
& $pythonPath $managePath test @testModules "--settings=$settings" --noinput --verbosity $Verbosity
exit $LASTEXITCODE
