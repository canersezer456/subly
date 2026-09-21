import uuid
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response

from lib.auth import get_current_user, hash_password, verify_password
from lib.db import db
from lib.seed import DEMO_EMAIL, seed_demo_finance, seed_starter_subscriptions
from models.auth import AuthCredentials, AuthRegister, AuthResponse, GoogleSessionRequest, UserPublic

router = APIRouter(prefix="/auth", tags=["auth"])


def _user_response(user: dict) -> UserPublic:
    return UserPublic(
        user_id=user["user_id"], email=user["email"], name=user.get("name", "Subly kullanıcısı"), picture=user.get("picture")
    )


async def _seed_starter_subscriptions(user_id: str, email: str = "") -> None:
    await seed_starter_subscriptions(user_id)
    if email == DEMO_EMAIL:
        await seed_demo_finance(user_id)


async def _create_session(user_id: str, response: Response, session_token: str | None = None) -> None:
    token = session_token or uuid.uuid4().hex + uuid.uuid4().hex
    await db.user_sessions.update_one(
        {"session_token": token},
        {"$set": {"user_id": user_id, "session_token": token, "created_at": datetime.now(timezone.utc), "expires_at": datetime.now(timezone.utc) + timedelta(days=7)}},
        upsert=True,
    )
    response.set_cookie("session_token", token, max_age=7 * 24 * 60 * 60, httponly=True, secure=True, samesite="none", path="/")


@router.post("/register", response_model=AuthResponse)
async def register(input: AuthRegister, response: Response, request: Request):
    email = str(input.email).lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=409, detail="Bu e-posta zaten kayıtlı")
    user = {"user_id": f"user_{uuid.uuid4().hex[:12]}", "email": email, "name": input.name, "password_hash": hash_password(input.password), "created_at": datetime.now(timezone.utc).isoformat()}
    await db.users.insert_one(user)
    await _seed_starter_subscriptions(user["user_id"])
    await _create_session(user["user_id"], response)
    return {"user": _user_response(user)}


@router.post("/login", response_model=AuthResponse)
async def login(input: AuthCredentials, response: Response, request: Request):
    email = str(input.email).lower()
    user = await db.users.find_one({"email": email}, {"_id": 0})
    if not user and email == "demo@subly.app" and input.password == "subly1234":
        user = {"user_id": "user_demo_subly", "email": email, "name": "Demo Kullanıcı", "password_hash": hash_password(input.password), "created_at": datetime.now(timezone.utc).isoformat()}
        await db.users.update_one({"email": email}, {"$setOnInsert": user}, upsert=True)
        user = await db.users.find_one({"email": email}, {"_id": 0})
    if not user or not verify_password(input.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="E-posta veya şifre hatalı")
    await _seed_starter_subscriptions(user["user_id"], email)
    await _create_session(user["user_id"], response)
    return {"user": _user_response(user)}


@router.get("/me", response_model=UserPublic | None)
async def me(request: Request):
    try:
        user = await get_current_user(request)
    except HTTPException:
        return None
    return _user_response(user)


@router.post("/logout", status_code=204)
async def logout(request: Request, response: Response):
    token = request.cookies.get("session_token")
    if token:
        await db.user_sessions.delete_one({"session_token": token})
    response.delete_cookie("session_token", path="/", secure=True, samesite="none")


@router.post("/google/session", response_model=AuthResponse)
async def google_session(input: GoogleSessionRequest, response: Response, request: Request):
    try:
        async with httpx.AsyncClient(timeout=12) as client:
            auth_response = await client.get("https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data", headers={"X-Session-ID": input.session_id})
        if auth_response.status_code != 200:
            raise HTTPException(status_code=401, detail="Google oturumu doğrulanamadı")
        profile = auth_response.json()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Google doğrulama servisine ulaşılamadı") from exc

    email = str(profile.get("email", "")).lower()
    if not email:
        raise HTTPException(status_code=400, detail="Google hesabında e-posta bulunamadı")
    user = await db.users.find_one({"email": email}, {"_id": 0})
    if not user:
        user = {"user_id": f"user_{uuid.uuid4().hex[:12]}", "email": email, "name": profile.get("name") or "Subly kullanıcısı", "picture": profile.get("picture"), "created_at": datetime.now(timezone.utc).isoformat()}
        await db.users.insert_one(user)
    else:
        await db.users.update_one({"user_id": user["user_id"]}, {"$set": {"name": profile.get("name") or user.get("name"), "picture": profile.get("picture")}})
        user = {**user, "name": profile.get("name") or user.get("name"), "picture": profile.get("picture")}
    await _seed_starter_subscriptions(user["user_id"])
    provider_token = profile.get("session_token")
    if not provider_token:
        raise HTTPException(status_code=401, detail="Google oturum anahtarı bulunamadı")
    await _create_session(user["user_id"], response, provider_token)
    return {"user": _user_response(user)}
