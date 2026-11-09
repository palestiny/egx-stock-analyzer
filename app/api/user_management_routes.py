from dataclasses import asdict
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from app.api.management_audit_response import ManagementAuditResponse
from app.api.user_audit_history_response import UserAuditHistoryResponse
from app.application.identity.get_management_audit import (
    GetManagementAudit,
    InvalidManagementAuditPageSizeError,
)
from app.application.identity.get_user_audit_history import (
    GetUserAuditHistory,
    InvalidUserAuditActionError,
    InvalidUserAuditPageSizeError,
)
from app.application.identity.user_management import UserManagementError, UserManagementService
from app.application.security.authorization import AuthorizationError
from app.application.security.identity import AuthenticatedIdentity, Permission
from app.application.security.operator_access import OperatorAccessError, OperatorAccessService
from app.domain.identity.user import UserStatus


def create_user_management_router(
    *,
    user_management: UserManagementService | None,
    get_management_audit: GetManagementAudit | None,
    get_user_audit_history: GetUserAuditHistory | None,
    require_authenticated,
    require_operator,
    operator_access: OperatorAccessService | None = None,
) -> APIRouter:
    """Register user and audit routes without owning authentication composition."""
    router = APIRouter()

    class OperatorAccessReasonPayload(BaseModel):
        reason: str = Field(min_length=1, max_length=500)

        @field_validator("reason")
        @classmethod
        def normalize_reason(cls, value: str) -> str:
            normalized = value.strip()
            if not normalized:
                raise ValueError("A non-empty reason is required")
            return normalized

    def require_individual_operator_identity(identity: AuthenticatedIdentity) -> None:
        if (
            Permission.OPERATOR not in identity.permissions
            or identity.user_id is None
            or identity.credential_id is None
        ):
            raise HTTPException(status_code=403, detail="Individual operator credential required")

    @router.get("/api/v1/operators/access-events")
    def list_operator_access_events(
        _identity: AuthenticatedIdentity = Depends(require_operator),
    ) -> dict[str, object]:
        if operator_access is None:
            raise HTTPException(status_code=503, detail="Operator access management is not configured")
        require_individual_operator_identity(_identity)
        events = operator_access.list_events(_identity)
        return {
            "items": [
                {
                    "event_id": event.event_id,
                    "action": event.action,
                    "target_user_id": str(event.target_user_id),
                    "actor_user_id": str(event.actor_user_id) if event.actor_user_id else None,
                    "actor_credential_id": str(event.actor_credential_id) if event.actor_credential_id else None,
                    "actor_kind": event.actor_kind,
                    "reason": event.reason,
                    "occurred_at": event.occurred_at.isoformat(),
                }
                for event in events
            ]
        }

    @router.post("/api/v1/operators/{user_id}/grant")
    def grant_operator_access(
        user_id: UUID,
        payload: OperatorAccessReasonPayload,
        identity: AuthenticatedIdentity = Depends(require_operator),
    ) -> dict[str, object]:
        if operator_access is None:
            raise HTTPException(status_code=503, detail="Operator access management is not configured")
        require_individual_operator_identity(identity)
        try:
            operator_access.grant(identity, user_id, payload.reason)
        except OperatorAccessError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        return {"user_id": str(user_id), "operator": True}

    @router.post("/api/v1/operators/{user_id}/revoke")
    def revoke_operator_access(
        user_id: UUID,
        payload: OperatorAccessReasonPayload,
        identity: AuthenticatedIdentity = Depends(require_operator),
    ) -> dict[str, object]:
        if operator_access is None:
            raise HTTPException(status_code=503, detail="Operator access management is not configured")
        require_individual_operator_identity(identity)
        try:
            operator_access.revoke(identity, user_id, payload.reason)
        except OperatorAccessError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        return {"user_id": str(user_id), "operator": False}

    @router.get("/api/v1/management/audit")
    def get_management_audit_report(
        actor_user_id: UUID | None = None,
        target_user_id: UUID | None = None,
        action: str | None = None,
        outcome: str | None = None,
        from_time: datetime | None = None,
        to_time: datetime | None = None,
        page_size: int = 50,
        offset: int = 0,
        identity: AuthenticatedIdentity = Depends(require_operator),
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

    @router.get("/api/v1/users/me/audit")
    def get_user_audit_history_report(
        action: str | None = None,
        outcome: str | None = None,
        from_time: datetime | None = None,
        to_time: datetime | None = None,
        page_size: int = 50,
        offset: int = 0,
        identity: AuthenticatedIdentity = Depends(require_authenticated),
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


    @router.get("/api/v1/users")
    def list_users(_identity: AuthenticatedIdentity = Depends(require_operator)) -> dict[str, object]:
        if user_management is None:
            raise HTTPException(status_code=503, detail="User management is not configured")
        users = user_management.list_users(_identity)
        return {
            "items": [
                {"user_id": str(user.id), "status": user.status.value}
                for user in users
            ]
        }

    @router.post("/api/v1/users")
    def create_user(_identity: AuthenticatedIdentity = Depends(require_operator)) -> dict[str, object]:
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

    @router.patch("/api/v1/users/{user_id}/status")
    def change_user_status(
        user_id: UUID,
        status: str,
        _identity: AuthenticatedIdentity = Depends(require_operator),
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

    @router.post("/api/v1/users/{user_id}/credentials/rotate")
    def rotate_user_credential(
        user_id: UUID,
        _identity: AuthenticatedIdentity = Depends(require_operator),
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

    @router.post("/api/v1/users/me/credentials/rotate")
    def rotate_own_credential(
        identity: AuthenticatedIdentity = Depends(require_authenticated),
    ) -> dict[str, object]:
        if user_management is None:
            raise HTTPException(status_code=503, detail="User management is not configured")
        try:
            credential = user_management.rotate_own_credential(identity)
        except UserManagementError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        return {"user_id": str(credential.user_id), "credential": credential.secret}


    return router
