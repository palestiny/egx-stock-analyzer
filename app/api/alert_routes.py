from __future__ import annotations

from dataclasses import asdict

from fastapi import Depends, FastAPI, HTTPException

from app.api.alert_candidate_response import AlertCandidateResponse
from app.api.alert_delivery_response import AlertDeliveryResponse
from app.api.authentication import ApiAuthentication
from app.application.notifications.deliver_alert_by_symbol import AlertCandidateNotFoundError, DeliverAlertBySymbol
from app.application.reporting.get_alert_candidate import GetAlertCandidate
from app.application.security.identity import AuthenticatedIdentity


def register_alert_routes(
    app: FastAPI,
    *,
    api_authentication: ApiAuthentication,
    deliver_alert_by_symbol: DeliverAlertBySymbol | None,
    get_alert_candidate: GetAlertCandidate | None,
) -> None:
    @app.post("/api/v1/alerts/{symbol}/deliver")
    def deliver_alert(
        symbol: str,
        channel: str,
        _identity: AuthenticatedIdentity = Depends(api_authentication.require_operator),
    ) -> dict[str, object]:
        if deliver_alert_by_symbol is None:
            raise HTTPException(status_code=503, detail="Alert delivery is not configured")
        try:
            record = deliver_alert_by_symbol.execute(symbol, channel)
        except AlertCandidateNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        response = AlertDeliveryResponse.from_record(record)
        return asdict(response)

    @app.get("/api/v1/alerts/{symbol}")
    def get_alert(
        symbol: str,
        _identity: AuthenticatedIdentity = Depends(api_authentication.require_operator),
    ) -> dict[str, object]:
        if get_alert_candidate is None:
            raise HTTPException(status_code=503, detail="Alert reporting is not configured")
        candidate = get_alert_candidate.execute(symbol)
        if candidate is None:
            raise HTTPException(status_code=404, detail=f"Alert candidate not found for {symbol}")
        response = AlertCandidateResponse.from_candidate(candidate)
        return asdict(response)
