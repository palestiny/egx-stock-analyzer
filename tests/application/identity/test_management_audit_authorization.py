from uuid import UUID

import pytest

from app.application.identity.get_management_audit import GetManagementAudit
from app.application.identity.management_audit import ManagementAuditPage
from app.application.security.authorization import AuthorizationError
from app.application.security.identity import AuthenticatedIdentity


class StubAuditStore:
    def read_page(self, query, *, offset, limit):
        return ManagementAuditPage(items=(), total_count=0, has_more=False)

    def append(self, event):
        raise AssertionError("append is not expected")


def test_management_audit_requires_operator_permission() -> None:
    service = GetManagementAudit(StubAuditStore())
    user = AuthenticatedIdentity.user(
        UUID("10000000-0000-0000-0000-000000000010")
    )

    with pytest.raises(AuthorizationError):
        service.execute(user)


def test_management_audit_accepts_operator_identity() -> None:
    page = GetManagementAudit(StubAuditStore()).execute(
        AuthenticatedIdentity.operator()
    )

    assert page.items == ()
    assert page.total_count == 0
