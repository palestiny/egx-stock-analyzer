# Telegram Bot Integration — EGX Stock Analyzer

This is an opt-in polling process. It delegates all analysis to the existing EGX API; it does not duplicate analytical logic.

## Commands

- `/start` or `/help`: command list.
- `/health`: check the API's public health endpoint.
- `/analyze EGAL`: request analysis through `POST /api/v1/analysis/EGAL`.
- `/report EGAL`: read the persisted report through `GET /api/v1/reports/EGAL`.
- `/alerts EGAL`: read the existing alert candidate through `GET /api/v1/alerts/EGAL`.

## Configuration (PowerShell)

Create a bot with Telegram's official BotFather and keep the token private. Do not commit either token to Git.

```powershell
$env:TELEGRAM_BOT_TOKEN = "your-telegram-bot-token"
$env:EGX_API_TOKEN = "your-existing-egx-api-bearer-token"
$env:EGX_API_BASE_URL = "http://127.0.0.1:8000"
$env:TELEGRAM_ALLOWED_USER_IDS = "your-numeric-telegram-user-id"
python -m app.telegram_bot
```

The API must already be running. Obtain your numeric Telegram user ID through a trusted method and configure an explicit allowlist. Empty or malformed allowlists fail closed. Do not expose the API bearer token to Telegram or put it in bot messages.

For a remote API, use HTTPS. Do not expose a development API directly to the public internet. The current integration uses an existing API bearer credential and is therefore intended for a restricted pilot with explicitly allowlisted users, not open public registration. A production multi-user release should provision per-user credentials and bind Telegram identities to internal EGX users rather than sharing an operator token.

## Test

```powershell
pytest tests/test_telegram_bot.py
ruff check app/telegram_bot.py tests/test_telegram_bot.py
```

The automated tests mock HTTP requests; they do not prove that a live Telegram token or live market-data provider works. Live acceptance requires starting the API, configuring the secrets locally, running the bot, and verifying `/health`, `/report EGAL`, and `/analyze EGAL` against available data.

## Current limits

- Long polling is used, so no public webhook endpoint is needed.
- The process must remain running to receive commands.
- `/analyze` invokes the existing analysis API and can therefore incur the normal provider latency/failure modes.
- Responses preserve the API payload instead of inventing price or signal fields.
- Automated alert push subscriptions and durable Telegram delivery/retry tracking are not part of this first integration slice.
