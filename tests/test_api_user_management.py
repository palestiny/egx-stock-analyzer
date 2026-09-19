from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.main import create_app
from app.application.analysis.result_store import InMemoryAnalysisResultStore
from app.application.identity.user_management import UserManagementService
from app.application.security.credentials import CredentialService
from app.application.security.identity import AuthenticatedIdentity
from app.domain.identity.user import User, UserStatus

class Users:
    def __init__(self):
        self.items={}
    def save(self,user): self.items[user.id]=user
    def get(self,user_id): return self.items.get(user_id)
    def get_or_create(self,user_id,status):
        return self.items.setdefault(user_id,User(user_id,status))

class Credentials:
    def __init__(self): self.items={}
    def create(self,c,v): self.items[c.id]=c
    def find_active_user_id(self,s): return None
    def find_active_credential(self,s): return None
    def find_active_for_user(self,user_id): return list(self.items.values())
    def replace(self,credential_id,user_id,replacement,replacement_verifier,revoked_at):
        self.items[replacement.id]=replacement
    def revoke(self,credential_id,revoked_at,replacement_id=None): pass

class Audit:
    def append(self,event): pass

def make_app():
    users=Users()
    legacy=User(__import__("app.application.security.identity",fromlist=["LEGACY_OPERATOR_USER_ID"]).LEGACY_OPERATOR_USER_ID,UserStatus.ACTIVE)
    users.save(legacy)
    service=UserManagementService(users,CredentialService(Credentials()),Audit())
    return create_app(
        InMemoryAnalysisResultStore(),
        user_management=service,
        operator_token="operator-token",
    )

def test_operator_can_create_user():
    with TestClient(make_app()) as client:
        response=client.post("/api/v1/users",headers={"Authorization":"Bearer operator-token"})
    assert response.status_code == 200
    assert response.json()["status"] == "active"
    assert response.json()["credential"]

def test_regular_user_cannot_create_user():
    user_id=uuid4()
    users=Users()
    users.save(User(user_id,UserStatus.ACTIVE))
    service=UserManagementService(users,CredentialService(Credentials()),Audit())
    from app.application.security.authentication import ConfiguredBearerTokenAuthenticator
    authenticator=ConfiguredBearerTokenAuthenticator(
        {"user-token":user_id},
        user_store=users,
    )
    app=create_app(InMemoryAnalysisResultStore(),user_management=service,authenticator=authenticator)
    with TestClient(app) as client:
        response=client.post("/api/v1/users",headers={"Authorization":"Bearer user-token"})
    assert response.status_code == 503
