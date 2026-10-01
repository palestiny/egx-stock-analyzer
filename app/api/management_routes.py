from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException

from app.api.management_audit_response import ManagementAuditResponse
from app.api.user_audit_history_response import UserAuditHistoryResponse
from app.api.authentication import ApiAuthentication
from app.application.identity.get_management_audit import (
    GetManagementAudit,
    InvalidManagementAuditPageSizeError,
)
from app.application.identity.get_user_audit_history import (
    GetUserAuditHistory,
    InvalidUserAuditActionError,
    InvalidUserAuditPageSizeError,
)
from app.application.identity.user_management import (
    UserManagementError,
    UserManagementService,
)
from app.application.security.authorization import AuthorizationError
from app.application.security.identity import AuthenticatedIdentity
from app.domain.identity.user import UserStatus


def register_management_routes(
    app: FastAPI,
    *,
    api_authentication: ApiAuthentication,
    user_management: UserManagementService | None,
    get_management_audit: GetManagementAudit | None,
    get_user_audit_history: GetUserAuditHistory | None,
) -> None:
@app.get("/api/v1/management/audit")
def get_management_audit_report(
    actor_user_id: UUID | None = None,
    target_user_id: UUID | None = None,
    action: str | None = None,
    outcome: str | None = None,
    from_time: datetime | None = None,
    to_time: datetime | None = None,
    page_size: int = 50,
    offset: int = 0,
    identity: AuthenticatedIdentity = Depends(api_authentication.require_operator),
) -> dict[str, object]:
    if get_management_audit is None:
        raise HTTPException(status_code=503, detail="Management audit reporting is not configured")
    try:
        page = get_management_audit.execute(
            identity,
            actor_user_id=actor_user_id,
            target_user_id=target_user_id,
            action=action,
            outcome=outcome,
            from_time=from_time,
            to_time=to_time,
            page_size=page_size,
            offset=offset,
        )
    except InvalidManagementAuditPageSizeError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return asdict(ManagementAuditResponse.from_page(page))

@app.get("/api/v1/users/me/audit")
def get_user_audit_history_report(
    action: str | None = None,
    outcome: str | None = None,
    from_time: datetime | None = None,
    to_time: datetime | None = None,
    page_size: int = 50,
    offset: int = 0,
    identity: AuthenticatedIdentity = Depends(api_authentication.require_authenticated),
) -> dict[str, object]:
    if get_user_audit_history is None:
        raise HTTPException(status_code=503, detail="User audit history is not configured")
    try:
        page = get_user_audit_history.execute(
            identity,
            action=action,
            outcome=outcome,
            from_time=from_time,
            to_time=to_time,
            page_size=page_size,
            offset=offset,
        )
    except InvalidUserAuditPageSizeError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except InvalidUserAuditActionError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return asdict(UserAuditHistoryResponse.from_page(page))


@app.get("/api/v1/users")
def list_users(_identity: AuthenticatedIdentity = Depends(api_authentication.require_operator)) -> dict[str, object]:
    if user_management is None:
        raise HTTPException(status_code=503, detail="User management is not configured")
    users = user_management.list_users(_identity)
    return {
        "items": [
            {"user_id": str(user.id), "status": user.status.value}
            for user in users
        ]
    }

@app.post("/api/v1/users")
def create_user(_identity: AuthenticatedIdentity = Depends(api_authentication.require_operator)) -> dict[str, object]:
    if user_management is None:
        raise HTTPException(status_code=503, detail="User management is not configured")
    try:
        user, credential = user_management.create_user(_identity)
    except AuthorizationError as error:
        raise HTTPException(status_code=403, detail="Forbidden") from error
    return {
        "user_id": str(user.id),
        "status": user.status.value,
        "credential": credential.secret,
    }

@app.patch("/api/v1/users/{user_id}/status")
def change_user_status(
    user_id: UUID,
    status: str,
    _identity: AuthenticatedIdentity = Depends(api_authentication.require_operator),
) -> dict[str, object]:
    if user_management is None:
        raise HTTPException(status_code=503, detail="User management is not configured")
    try:
        requested = UserStatus(status)
    except ValueError as error:
        raise HTTPException(status_code=400, detail="Invalid user status") from error
    try:
        user = user_management.set_status(_identity, user_id, requested)
    except UserManagementError as error:
        if str(error) == "User not found":
            raise HTTPException(status_code=404, detail=str(error)) from error
        raise HTTPException(status_code=409, detail=str(error)) from error
    return {"user_id": str(user.id), "status": user.status.value}

@app.post("/api/v1/users/{user_id}/credentials/rotate")
def rotate_user_credential(
    user_id: UUID,
    _identity: AuthenticatedIdentity = Depends(api_authentication.require_operator),
) -> dict[str, object]:
    if user_management is None:
        raise HTTPException(status_code=503, detail="User management is not configured")
    try:
        credential = user_management.rotate_user_credential(_identity, user_id)
    except UserManagementError as error:
        if str(error) == "User not found":
            raise HTTPException(status_code=404, detail=str(error)) from error
        raise HTTPException(status_code=409, detail=str(error)) from error
    return {"user_id": str(credential.user_id), "credential": credential.secret}

@app.post("/api/v1/users/me/credentials/rotate")
def rotate_own_credential(
    identity: AuthenticatedIdentity = Depends(api_authentication.require_authenticated),
) -> dict[str, object]:
    if user_management is None:
        raise HTTPException(status_code=503, detail="User management is not configured")
    try:
        credential = user_management.rotate_own_credential(identity)
    except UserManagementError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return {"user_id": str(credential.user_id), "credential": credential.secret}


