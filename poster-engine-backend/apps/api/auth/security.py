from pydantic import BaseModel


class AuthenticatedUser(BaseModel):
    user_id: str
    workspace_id: str | None = None
    email: str | None = None
