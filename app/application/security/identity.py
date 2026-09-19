from dataclasses import dataclass
from enum import Enum


class Permission(str, Enum):
    OPERATOR = "operator"


@dataclass(frozen=True)
class AuthenticatedIdentity:
    subject: str
    permissions: frozenset[Permission]

    @classmethod
    def operator(cls) -> "AuthenticatedIdentity":
        return cls(
            subject="operator",
            permissions=frozenset({Permission.OPERATOR}),
        )
