from pydantic import BaseModel, EmailStr, Field


class UserPublic(BaseModel):
    user_id: str
    email: EmailStr
    name: str
    picture: str | None = None


class AuthCredentials(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class AuthRegister(AuthCredentials):
    name: str = Field(min_length=2, max_length=80)


class GoogleSessionRequest(BaseModel):
    session_id: str = Field(min_length=8)


class AuthResponse(BaseModel):
    user: UserPublic
