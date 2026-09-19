from dataclasses import dataclass
from enum import Enum
from uuid import UUID

from app.domain.identity.user import UserStatus


LEGACY_OPERATOR_USER_ID = UUID("00000000-0000-0000-0000-000000000001")


class Permission(str, Enum):
    OPERATOR = "operator"


@dataclass(frozen=True)
class AuthenticatedIdentity:
    subject: str
    permissions: frozenset[Permission]
    user_id: UUID | None = None
    user_status: UserStatus | None = None

    @classmethod
    def operator(cls) -> "AuthenticatedIdentity":
        return cls(
            subject="operator",
            permissions=frozenset({Permission.OPERATOR}),
            user_id=LEGACY_OPERATOR_USER_ID,
            user_status=UserStatus.ACTIVE,
        )

    @classmethod
    def user(
        cls,
        user_id: UUID,
        status: UserStatus = UserStatus.ACTIVE,
    ) -> "AuthenticatedIdentity":
        return cls(
            subject=str(user_id),
            permissions=frozenset(),
            user_id=user_id,
            user_status=status,
        )
