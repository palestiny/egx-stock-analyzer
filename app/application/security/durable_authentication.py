from secrets import compare_digest

from app.application.identity.user_store import UserStore
from app.application.security.authentication import AuthenticationError, ConfiguredBearerTokenAuthenticator
from app.application.security.credentials import CredentialStore
from app.application.security.identity import AuthenticatedIdentity
from app.domain.identity.user import UserStatus


class DurableBearerTokenAuthenticator:
    def __init__(
        self,
        credential_store: CredentialStore,
        user_store: UserStore,
        fallback: ConfiguredBearerTokenAuthenticator | None = None,
    ) -> None:
        self._credential_store = credential_store
        self._user_store = user_store
        self._fallback = fallback

    def authenticate(self, authorization_header: str | None) -> AuthenticatedIdentity:
        token = self._extract_token(authorization_header)
        user_id = self._credential_store.find_active_user_id(token)

        if user_id is not None:
            user = self._user_store.get(user_id)
            if user is not None and user.status is UserStatus.ACTIVE:
                return AuthenticatedIdentity.user(user.id, user.status)

        if self._fallback is not None:
            return self._fallback.authenticate("Bearer " + token)

        raise AuthenticationError("Authentication credentials are invalid")

    @staticmethod
    def _extract_token(authorization_header: str | None) -> str:
        if not authorization_header:
            raise AuthenticationError("Authentication credentials are required")

        scheme, separator, token = authorization_header.partition(" ")
        if not separator or scheme.lower() != "bearer" or not token.strip():
            raise AuthenticationError("Authentication credentials are invalid")

        return token.strip()
