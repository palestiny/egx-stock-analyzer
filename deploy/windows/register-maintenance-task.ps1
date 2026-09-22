[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$RepositoryPath,
    [Parameter(Mandatory = $true)][string]$PythonPath,
    [Parameter(Mandatory = $true)][string]$DatabasePath,
    [string]$TaskName = "EGX Stock Analyzer - Automatic Retention",
    [string]$LogDirectory = "$env:ProgramData\EGXStockAnalyzer\maintenance",
    [string]$TaskUser = "$env:USERNAME"
)
$ErrorActionPreference = "Stop"
$wrapper = Join-Path $RepositoryPath "deploy\windows\run-maintenance.ps1"
if (-not (Test-Path $wrapper)) { throw "Maintenance wrapper not found: $wrapper" }
New-Item -ItemType Directory -Force -Path $LogDirectory | Out-Null
$arguments = '-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "' + $wrapper + '" -RepositoryPath "' + $RepositoryPath + '" -PythonPath "' + $PythonPath + '" -DatabasePath "' + $DatabasePath + '" -LogDirectory "' + $LogDirectory + '"'
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $arguments
$trigger = New-ScheduledTaskTrigger -Daily -At "03:30"
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 30) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 10) -StartWhenAvailable
$principal = New-ScheduledTaskPrincipal -UserId $TaskUser -LogonType InteractiveToken -RunLevel Limited
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force | Out-Null
Write-Host "Registered scheduled task: $TaskName"
