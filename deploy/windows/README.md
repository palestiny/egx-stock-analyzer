# Windows Production Maintenance Scheduling

This directory maps M60 to Windows Task Scheduler.

## Boundary

Windows Task Scheduler
  -> run-maintenance.ps1
  -> python -m app.infrastructure.maintenance.automatic_retention_command
  -> AutomaticAnalysisRetention (M58)
  -> PurgeAnalysisLifecycle (M57)

The PowerShell tooling contains no retention or deletion logic.

## Accepted schedule

- Daily at 03:30 local host time.
- Ignore a new invocation while one is running.
- 30-minute execution ceiling.
- Up to 3 scheduler restarts, 10 minutes apart.
- Dry-run is operator-only and is not scheduled.

## Registration

Run PowerShell with the required deployment privileges:

    .\deploy\windows\register-maintenance-task.ps1 -RepositoryPath "C:\Apps\EGXStockAnalyzer" -PythonPath "C:\Apps\EGXStockAnalyzer\.venv\Scripts\python.exe" -DatabasePath "C:\Apps\EGXStockAnalyzer\storage\analysis.db"

The default task principal is the current Windows user. For unattended production deployment, register the task under the deployment service account according to the host credential policy. Credentials must never be committed to the repository.

## Removal

    .\deploy\windows\unregister-maintenance-task.ps1

## Verification

1. Confirm the daily trigger is 03:30 local time.
2. Confirm overlap is IgnoreNew.
3. Confirm the 30-minute limit and retry settings.
4. Run the wrapper manually with retention disabled and confirm exit code 0 and no deletion.
5. Enable M58 only through existing application configuration.
6. Confirm a normal invocation returns the maintenance command exit code.
7. Confirm Task Scheduler history records failures.
8. Confirm M57/M58 audit records remain the application-level maintenance record.

The scripts are deployment tooling only; they are not part of the application domain or API.
