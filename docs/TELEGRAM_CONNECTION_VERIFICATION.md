# Telegram Bot connection and live-send verification

The application reads Telegram configuration from environment variables:

- `EGX_TELEGRAM_BOT_TOKEN`: bot token from BotFather.
- `EGX_TELEGRAM_CHAT_ID`: destination chat ID (a private chat, group, or channel where the bot is allowed to post).
- `EGX_TELEGRAM_TIMEOUT_SECONDS`: optional request timeout; defaults to 10 seconds.

Both token and chat ID must be configured together. Do not put real credentials in source code, commit them, paste them into issue comments, or include them in logs.

## Automated test (no Telegram connection)

The deterministic provider tests use `httpx.MockTransport`; they do not send messages and do not need credentials:

```powershell
python -m pytest tests/test_telegram_notification_provider.py -q
```

These tests are part of the normal unit-test suite and CI.

## Real send (explicit opt-in)

The real-send test is marked `integration` and `external`, so normal CI explicitly excludes it. It sends one clearly labeled `connection_test` message to the configured chat. Run it only when you intend to send that message.

In the same PowerShell session, set the three environment variables without putting the token in a command literal or source file. For example, obtain the token through a secure prompt or your secret manager, and set the chat ID locally. Then run:

```powershell
$env:EGX_TELEGRAM_LIVE_TEST = "1"
python -m pytest -m external tests/integration/test_telegram_live_delivery.py -q
```

If the opt-in flag is absent, the live test skips. If the flag is present but credentials are missing, it fails with a generic configuration message without printing their values. After the test, clear the session variables:

```powershell
Remove-Item Env:EGX_TELEGRAM_LIVE_TEST -ErrorAction SilentlyContinue
Remove-Item Env:EGX_TELEGRAM_BOT_TOKEN -ErrorAction SilentlyContinue
Remove-Item Env:EGX_TELEGRAM_CHAT_ID -ErrorAction SilentlyContinue
```

A passing live test verifies Telegram accepted the message. It does not prove that the bot's scheduled analysis, alert eligibility, or production scheduler has been exercised end-to-end. The API's `POST /api/v1/alerts/{symbol}/deliver?channel=telegram` path additionally requires an existing alert candidate for that symbol.

## Secret handling

Transport errors are converted to sanitized provider errors without chaining low-level HTTP exceptions, because request URLs contain the bot token. Never enable verbose HTTP wire logging while using a real bot token.
