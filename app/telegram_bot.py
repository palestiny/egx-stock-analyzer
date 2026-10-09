"""Minimal Telegram polling adapter for EGX Stock Analyzer.

This is an opt-in integration process. It talks to the existing authenticated API;
it does not implement analysis rules or expose the API token to Telegram users.
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
from typing import Any

import httpx

LOGGER = logging.getLogger("egx.telegram")
SYMBOL_PATTERN = re.compile(r"^[A-Z0-9._-]{1,20}$")


def parse_symbol(text: str) -> str | None:
    """Return a normalized stock symbol from a command argument."""
    symbol = text.strip().upper()
    return symbol if SYMBOL_PATTERN.fullmatch(symbol) else None


def allowed_chat_ids(raw: str) -> frozenset[int]:
    """Parse a required comma-separated allowlist of Telegram numeric user IDs."""
    values = [part.strip() for part in raw.split(",") if part.strip()]
    if not values:
        raise ValueError("TELEGRAM_ALLOWED_USER_IDS must contain at least one numeric user ID")
    try:
        parsed = frozenset(int(value) for value in values)
    except ValueError as exc:
        raise ValueError("TELEGRAM_ALLOWED_USER_IDS must contain only numeric IDs") from exc
    if any(value <= 0 for value in parsed):
        raise ValueError("Telegram user IDs must be positive integers")
    return parsed


class EgxTelegramBot:
    def __init__(
        self,
        telegram_token: str,
        api_base_url: str,
        api_token: str,
        allowed_user_ids: frozenset[int],
        *,
        http: httpx.AsyncClient | None = None,
    ) -> None:
        if not telegram_token.strip() or not api_token.strip():
            raise ValueError("Telegram and EGX API tokens are required")
        self.telegram_token = telegram_token
        self.telegram_url = f"https://api.telegram.org/bot{telegram_token}"
        self.api_base_url = api_base_url.rstrip("/")
        self.api_token = api_token
        self.allowed_user_ids = allowed_user_ids
        self.http = http or httpx.AsyncClient(timeout=httpx.Timeout(20.0))
        self._owns_http = http is None
        self._offset = 0

    async def close(self) -> None:
        if self._owns_http:
            await self.http.aclose()

    async def _telegram(self, method: str, **payload: Any) -> Any:
        response = await self.http.post(f"{self.telegram_url}/{method}", json=payload)
        response.raise_for_status()
        body = response.json()
        if not body.get("ok"):
            raise RuntimeError(f"Telegram API rejected {method}")
        return body.get("result")

    async def _api_get(self, path: str) -> dict[str, Any]:
        response = await self.http.get(
            f"{self.api_base_url}{path}",
            headers={"Authorization": f"Bearer {self.api_token}"},
        )
        response.raise_for_status()
        body = response.json()
        return body if isinstance(body, dict) else {"result": body}

    async def _api_post(self, path: str) -> dict[str, Any]:
        response = await self.http.post(
            f"{self.api_base_url}{path}",
            headers={"Authorization": f"Bearer {self.api_token}"},
        )
        response.raise_for_status()
        body = response.json()
        return body if isinstance(body, dict) else {"result": body}

    async def _reply(self, chat_id: int, text: str) -> None:
        # Telegram messages have a 4096-character limit; leave room for safety.
        await self._telegram("sendMessage", chat_id=chat_id, text=text[:4000])

    async def handle_message(self, message: dict[str, Any]) -> None:
        sender = message.get("from") or {}
        chat = message.get("chat") or {}
        user_id = sender.get("id")
        chat_id = chat.get("id")
        text = message.get("text", "")
        if not isinstance(user_id, int) or not isinstance(chat_id, int):
            return
        # Private chats only: never leak analysis/report payloads into groups.
        if chat.get("type") != "private":
            await self._reply(chat_id, "استخدم البوت في محادثة خاصة فقط لحماية بيانات التحليل.")
            return
        if user_id not in self.allowed_user_ids:
            LOGGER.warning("Rejected Telegram user id=%s", user_id)
            await self._reply(chat_id, "غير مصرح لك باستخدام بوت EGX. تواصل مع المسؤول.")
            return
        if not isinstance(text, str) or not text.startswith("/"):
            return

        parts = text.strip().split(maxsplit=1)
        command = parts[0].split("@", maxsplit=1)[0].lower()
        argument = parts[1] if len(parts) == 2 else ""

        if command in {"/start", "/help"}:
            await self._reply(
                chat_id,
                "EGX Stock Analyzer\n"
                "/health — فحص اتصال النظام\n"
                "/analyze SYMBOL — تشغيل تحليل سهم\n"
                "/report SYMBOL — عرض آخر تقرير محفوظ\n"
                "/alerts SYMBOL — عرض حالة التنبيه\n"
                "مثال: /analyze EGAL",
            )
            return
        if command == "/health":
            try:
                response = await self.http.get(f"{self.api_base_url}/health")
                response.raise_for_status()
                await self._reply(chat_id, "✅ واجهة EGX تعمل.")
            except httpx.HTTPError:
                await self._reply(chat_id, "❌ واجهة EGX غير متاحة حاليًا.")
            return
        if command not in {"/analyze", "/report", "/alerts"}:
            await self._reply(chat_id, "أمر غير معروف. استخدم /help.")
            return
        symbol = parse_symbol(argument)
        if symbol is None:
            await self._reply(chat_id, "اكتب رمز سهم صحيحًا، مثال: /analyze EGAL")
            return

        try:
            if command == "/analyze":
                result = await self._api_post(f"/api/v1/analysis/{symbol}")
                await self._reply(chat_id, f"تم تنفيذ طلب تحليل {symbol}.\n{self._summarize(result)}")
            elif command == "/report":
                result = await self._api_get(f"/api/v1/reports/{symbol}")
                await self._reply(chat_id, f"التقرير المحفوظ — {symbol}\n{self._summarize(result)}")
            else:
                result = await self._api_get(f"/api/v1/alerts/{symbol}")
                await self._reply(chat_id, f"حالة التنبيه — {symbol}\n{self._summarize(result)}")
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            LOGGER.warning("EGX API request failed command=%s status=%s", command, status)
            if status == 404:
                detail = "لا توجد نتيجة محفوظة أو أن السهم غير متاح."
            elif status in {401, 403}:
                detail = "فشل التحقق من صلاحية اتصال البوت بواجهة EGX."
            else:
                detail = f"فشل الطلب (HTTP {status}). حاول لاحقًا."
            await self._reply(chat_id, detail)
        except (httpx.HTTPError, ValueError):
            LOGGER.exception("EGX API request failed command=%s", command)
            await self._reply(chat_id, "تعذر الاتصال بواجهة EGX حاليًا. لم يتم إنشاء نتيجة بديلة.")

    @staticmethod
    def _summarize(payload: dict[str, Any]) -> str:
        """Keep the first-party API response truthful without assuming its schema."""
        import json

        rendered = json.dumps(payload, ensure_ascii=False, default=str)
        return rendered if len(rendered) <= 3200 else rendered[:3190] + "…"

    async def run(self, poll_seconds: float = 1.0) -> None:
        LOGGER.info("EGX Telegram bot polling started")
        try:
            while True:
                try:
                    updates = await self._telegram(
                        "getUpdates",
                        offset=self._offset,
                        timeout=20,
                        allowed_updates=["message"],
                    )
                    for update in updates or []:
                        self._offset = max(self._offset, int(update.get("update_id", 0)) + 1)
                        message = update.get("message")
                        if isinstance(message, dict):
                            try:
                                await self.handle_message(message)
                            except (httpx.HTTPError, RuntimeError):
                                LOGGER.exception("Failed to process Telegram update")
                except (httpx.HTTPError, RuntimeError, ValueError):
                    LOGGER.exception("Telegram polling request failed")
                    await asyncio.sleep(max(poll_seconds, 2.0))
        finally:
            await self.close()


async def main() -> None:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    api_token = os.getenv("EGX_API_TOKEN", "")
    api_base = os.getenv("EGX_API_BASE_URL", "http://127.0.0.1:8000")
    allowed = allowed_chat_ids(os.getenv("TELEGRAM_ALLOWED_USER_IDS", ""))
    if not token or not api_token:
        raise RuntimeError("Set TELEGRAM_BOT_TOKEN and EGX_API_TOKEN before starting the bot")
    bot = EgxTelegramBot(token, api_base, api_token, allowed)
    try:
        # Validate the credential before entering long polling. Without this,
        # an invalid token only produces repeated polling errors with no clear
        # indication that the service is unusable.
        identity = await bot._telegram("getMe")
        bot_name = identity.get("username", "unknown") if isinstance(identity, dict) else "unknown"
        LOGGER.info("Telegram credentials validated; bot_username=%s", bot_name)

        # Send a startup receipt to the allowlisted private users. Telegram
        # user IDs are also their private-chat IDs after they have started the bot.
        for user_id in sorted(allowed):
            await bot._reply(
                user_id,
                f"✅ بوت EGX اشتغل بنجاح (@{bot_name}).\\n"
                "اكتب /health للتأكد من اتصال واجهة التحليل، أو /help لعرض الأوامر.",
            )
        await bot.run()
    except BaseException:
        LOGGER.exception("Telegram bot failed during startup or shutdown")
        raise
    finally:
        await bot.close()


if __name__ == "__main__":
    asyncio.run(main())
