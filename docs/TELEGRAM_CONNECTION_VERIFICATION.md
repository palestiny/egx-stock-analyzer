# Telegram Bot connection and live-send verification

The application reads Telegram configuration from environment variables:

- `EGX_TELEGRAM_BOT_TOKEN`: bot token from BotFather.
- `EGX_TELEGRAM_CHAT_ID`: destination chat ID (a private chat, group, or channel where the bot is allowed to post).
- `EGX_TELEGRAM_TIMEOUT_SECONDS`: optional request timeout; defaults to 10 seconds.

For legacy single-destination alert delivery, configure both the bot token and chat ID. For the account-linking bot flow, the token may be configured without a default chat ID; legacy automatic alert delivery remains disabled unless both are present. The webhook flow also requires `EGX_TELEGRAM_WEBHOOK_SECRET`, configured as the Telegram webhook's `secret_token` and sent by Telegram in `X-Telegram-Bot-Api-Secret-Token`.

Do not put real credentials or the webhook secret in source code, commit them, paste them into issue comments, or include them in logs.

## Automated test (no Telegram connection)

The deterministic provider tests use `httpx.MockTransport`; they do not send messages and do not need credentials:

```powershell
python -m pytest tests/test_telegram_notification_provider.py -q
```

These tests are part of the normal unit-test suite and CI.

## Real send (explicit opt-in)

The real-send test is marked `integration` and `external`, so normal CI explicitly excludes it. It sends one clearly labeled `connection_test` message to the configured chat. Run it only when you intend to send that message.

From the repository root, run the helper. It prompts for the bot token with hidden input, prompts for the destination chat ID, sets the environment variables only for the duration of the script, and removes them in a `finally` block. The token is not placed in shell command history or printed by the script:

```powershell
.\scripts\test_telegram_live.ps1
```

If the opt-in flag is absent, the live test skips. If the flag is present but credentials are missing, it fails with a generic configuration message without printing their values. The helper clears the environment variables automatically, including when the test fails.

A passing live test verifies Telegram accepted the message. It does not prove that the bot's scheduled analysis, alert eligibility, or production scheduler has been exercised end-to-end. The API's `POST /api/v1/alerts/{symbol}/deliver?channel=telegram` path additionally requires an existing alert candidate for that symbol.

## Secret handling

Transport errors are converted to sanitized provider errors without chaining low-level HTTP exceptions, because request URLs contain the bot token. Never enable verbose HTTP wire logging while using a real bot token.


## Account linking webhook (no live send during tests)

- Configure `EGX_TELEGRAM_BOT_TOKEN` and a strong `EGX_TELEGRAM_WEBHOOK_SECRET`.
- Publish the API behind HTTPS and register Telegram's webhook URL ending in `/api/v1/telegram/webhook`, setting the same secret as Telegram's `secret_token`.
- An authenticated web user calls `POST /api/v1/telegram/link-challenges` with their bearer token. The response contains a one-time token that expires after 10 minutes by default.
- The user sends `/start <token>` to the bot in a private chat. The webhook verifies Telegram's secret header and consumes the token once; only then is that chat linked to the authenticated account.
- The authenticated user can call `DELETE /api/v1/telegram/link` to unlink the current chat.
- The application stores a hash of the link token, not its plaintext value. Link-event history stores a hash of chat IDs rather than the raw ID.
- Do not expose the link token in logs or analytics. Treat it as a temporary credential.

This establishes account linking only. Subscriber-aware opportunity delivery must still apply server-side entitlements and per-recipient delivery idempotency before sending premium messages.
