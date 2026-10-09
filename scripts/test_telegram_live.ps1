$ErrorActionPreference = "Stop"

$secureToken = Read-Host "Telegram bot token (input hidden)" -AsSecureString
$chatId = Read-Host "Telegram destination chat ID"
$tokenPointer = [IntPtr]::Zero
$testExitCode = 1

try {
    $tokenPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureToken)
    $env:EGX_TELEGRAM_BOT_TOKEN = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($tokenPointer)
    $env:EGX_TELEGRAM_CHAT_ID = $chatId.Trim()
    $env:EGX_TELEGRAM_LIVE_TEST = "1"

    python -m pytest -m external tests/integration/test_telegram_live_delivery.py -q
    $testExitCode = $LASTEXITCODE
}
finally {
    if ($tokenPointer -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($tokenPointer)
    }

    Remove-Item Env:EGX_TELEGRAM_BOT_TOKEN -ErrorAction SilentlyContinue
    Remove-Item Env:EGX_TELEGRAM_CHAT_ID -ErrorAction SilentlyContinue
    Remove-Item Env:EGX_TELEGRAM_LIVE_TEST -ErrorAction SilentlyContinue
    $secureToken.Dispose()
}

if ($testExitCode -ne 0) {
    exit $testExitCode
}
