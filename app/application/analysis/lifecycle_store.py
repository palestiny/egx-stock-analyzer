from typing import Protocol
from uuid import UUID


class AnalysisLifecycleStore(Protocol):
    def delete_run(
        self,
        run_id: UUID,
        actor_user_id: UUID,
        target_user_id: UUID | None,
    ) -> bool:
        ...

    def delete_snapshot(
        self,
        snapshot_id: UUID,
        actor_user_id: UUID,
        target_user_id: UUID | None,
    ) -> bool:
        ...
