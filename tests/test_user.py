from uuid import UUID

from app.domain.identity.user import User, UserStatus


USER_ID = UUID("00000000-0000-0000-0000-00000000000a")


def test_active_user_can_access_protected_resources():
    assert User(USER_ID, UserStatus.ACTIVE).can_access_protected_resources()


def test_disabled_user_cannot_access_protected_resources():
    assert not User(USER_ID, UserStatus.DISABLED).can_access_protected_resources()


def test_deleted_user_cannot_access_protected_resources():
    assert not User(USER_ID, UserStatus.DELETED).can_access_protected_resources()
