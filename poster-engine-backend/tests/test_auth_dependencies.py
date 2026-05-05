import jwt
from fastapi import HTTPException

from apps.api.auth.dependencies import get_current_user
from apps.api.core.config import settings


class _Creds:
    def __init__(self, token: str):
        self.credentials = token


def test_get_current_user_from_jwt():
    settings.auth_jwt_secret = "test-secret"
    settings.auth_jwt_algorithm = "HS256"
    token = jwt.encode({"sub": "user_123", "email": "u@example.com"}, settings.auth_jwt_secret, algorithm=settings.auth_jwt_algorithm)

    user = get_current_user(_Creds(token))
    assert user.user_id == "user_123"
    assert user.email == "u@example.com"


def test_get_current_user_rejects_invalid_token():
    settings.auth_jwt_secret = "test-secret"
    settings.auth_jwt_algorithm = "HS256"
    try:
        get_current_user(_Creds("bad-token"))
        assert False, "expected HTTPException"
    except HTTPException as exc:
        assert exc.status_code == 401
