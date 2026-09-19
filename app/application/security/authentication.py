from collections.abc import Mapping
from secrets import compare_digest
from uuid import UUID

from app.application.identity.user_store import UserStore
from app.application.security.identity import (
    AuthenticatedIdentity,
    LEGACY_OPERATOR_USER_ID,
)
from app.domain.identity.user import UserStatus

