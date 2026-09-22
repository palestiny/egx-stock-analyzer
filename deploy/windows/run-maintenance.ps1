[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$RepositoryPath,
    [Parameter(Mandatory = $true)][string]$PythonPath,
    [Parameter(Mandatory = $true)][string]$DatabasePath,
    [string]$LogDirectory = "$env:ProgramData\EGXStockAnalyzer\maintenance"
)
$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force -Path $LogDirectory | Out-Null
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$logPath = Join-Path $LogDirectory "retention-$timestamp.log"
Push-Location $RepositoryPath
try {
    $output = & $PythonPath -m app.infrastructure.maintenance.automatic_retention_command --database $DatabasePath 2>&1
    $exitCode = $LASTEXITCODE
    $output | Tee-Object -FilePath $logPath
    exit $exitCode
}
finally { Pop-Location }
