import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from apps.api.auth.security import AuthenticatedUser
from apps.api.core.config import settings

bearer_scheme = HTTPBearer(auto_error=True)


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> AuthenticatedUser:
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            settings.auth_jwt_secret,
            algorithms=[settings.auth_jwt_algorithm],
            options={"verify_aud": False},
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail=f"Invalid token: {exc}") from exc

    subject = payload.get("sub")
    if not subject:
        raise HTTPException(status_code=401, detail="Token missing sub claim")

    return AuthenticatedUser(
        user_id=str(subject),
        workspace_id=payload.get("workspace_id"),
        email=payload.get("email"),
    )
