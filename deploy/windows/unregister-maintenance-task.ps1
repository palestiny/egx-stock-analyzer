[CmdletBinding()]
param([string]$TaskName = "EGX Stock Analyzer - Automatic Retention")
$ErrorActionPreference = "Stop"
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
Write-Host "Removed scheduled task: $TaskName"
