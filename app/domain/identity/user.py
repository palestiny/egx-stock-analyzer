from dataclasses import dataclass
from enum import Enum
from uuid import UUID


class UserStatus(str, Enum):
    ACTIVE = "active"
    DISABLED = "disabled"
    DELETED = "deleted"


@dataclass(frozen=True)
class User:
    id: UUID
    status: UserStatus

    def can_access_protected_resources(self) -> bool:
        return self.status is UserStatus.ACTIVE
