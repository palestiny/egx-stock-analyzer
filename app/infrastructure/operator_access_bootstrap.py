from __future__ import annotations

import argparse
from uuid import UUID

from app.infrastructure.persistence.sqlite_credential_store import SQLiteCredentialStore
from app.infrastructure.persistence.sqlite_operator_access_store import SQLiteOperatorAccessStore
from app.infrastructure.persistence.sqlite_user_store import SQLiteUserStore


def bootstrap_first_operator(database_path: str, user_id: UUID, reason: str) -> None:
    """Grant the first operator from a trusted local administrative environment."""
    users = SQLiteUserStore(database_path)
    credentials = SQLiteCredentialStore(database_path)
    if users.get(user_id) is None:
        raise ValueError("Target user does not exist")
    if not credentials.find_active_for_user(user_id):
        raise ValueError("Target user must have an active durable credential")
    SQLiteOperatorAccessStore(database_path).bootstrap_first_operator(
        user_id,
        reason=reason,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Bootstrap the first individually authenticated EGX operator."
    )
    parser.add_argument("--database-path", required=True)
    parser.add_argument("--user-id", required=True, type=UUID)
    parser.add_argument("--reason", required=True)
    args = parser.parse_args()
    bootstrap_first_operator(args.database_path, args.user_id, args.reason)
    print(f"First EGX operator access granted to {args.user_id}")


if __name__ == "__main__":
    main()
