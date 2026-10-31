from dataclasses import asdict
from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.application.security.identity import AuthenticatedIdentity
from app.application.alerts.telegram_delivery_reconciliation import (
    TelegramDeliveryReconciliationStore,
)


class ReconcileTelegramDeliveryRequest(BaseModel):
    outcome: Literal["CONFIRMED_DELIVERED", "CONFIRMED_NOT_DELIVERED"]
    reason: str = Field(min_length=3, max_length=1000)


def create_telegram_delivery_reconciliation_router(
    *,
    store: TelegramDeliveryReconciliationStore | None,
    require_operator,
) -> APIRouter:
    router = APIRouter()

    @router.get("/api/v1/management/telegram-deliveries/unresolved")
    def list_unresolved(
        limit: int = 50,
        offset: int = 0,
        _identity: AuthenticatedIdentity = Depends(require_operator),
    ) -> dict[str, object]:
        if store is None:
            raise HTTPException(status_code=503, detail="Telegram delivery reconciliation is not configured")
        try:
            items = store.list_unresolved(limit=limit, offset=offset)
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        return {"items": list(items), "limit": limit, "offset": offset}

    @router.post("/api/v1/management/telegram-deliveries/{event_id}/{user_id}/reconcile")
    def reconcile_delivery(
        event_id: UUID,
        user_id: UUID,
        request: ReconcileTelegramDeliveryRequest,
        channel: str = "telegram",
        identity: AuthenticatedIdentity = Depends(require_operator),
    ) -> dict[str, object]:
        if store is None:
            raise HTTPException(status_code=503, detail="Telegram delivery reconciliation is not configured")
        try:
            result = store.reconcile(
                event_id, user_id, channel,
                outcome=request.outcome,
                actor_subject=identity.subject,
                reason=request.reason,
                now=datetime.now(timezone.utc),
            )
        except LookupError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        return asdict(result)

    @router.get("/api/v1/management/telegram-deliveries/reconciliation-audit")
    def list_reconciliation_audit(
        limit: int = 50,
        offset: int = 0,
        _identity: AuthenticatedIdentity = Depends(require_operator),
    ) -> dict[str, object]:
        if store is None:
            raise HTTPException(status_code=503, detail="Telegram delivery reconciliation is not configured")
        try:
            items = store.list_audit(limit=limit, offset=offset)
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        return {"items": [asdict(item) for item in items], "limit": limit, "offset": offset}

    return router
