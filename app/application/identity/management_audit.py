from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

@dataclass(frozen=True)
class ManagementAuditEvent:
    actor_user_id: UUID
    action: str
    target_user_id: UUID
    occurred_at: datetime
    outcome: str

class ManagementAuditStore(Protocol):
    def append(self, event: ManagementAuditEvent) -> None:
        ...
