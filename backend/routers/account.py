from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request, Response

from lib.auth import get_current_user
from lib.db import db
from models.finance import AccountExport

router = APIRouter(prefix="/account", tags=["account"])
USER_COLLECTIONS = ("incomes", "expenses", "bills", "budgets", "subscriptions", "assistant_messages", "assistant_usage", "digest_prefs")


@router.get("/export", response_model=AccountExport)
async def export_account(user: dict = Depends(get_current_user)):
    payload = {"exported_at": datetime.now(timezone.utc).isoformat(), "user": {k: v for k, v in user.items() if k != "password_hash"}}
    for name in USER_COLLECTIONS:
        payload[name] = await db[name].find({"user_id": user["user_id"]}, {"_id": 0}).to_list(5000)
    return payload


@router.delete("", status_code=204)
async def delete_account(request: Request, response: Response, user: dict = Depends(get_current_user)):
    for name in USER_COLLECTIONS:
        await db[name].delete_many({"user_id": user["user_id"]})
    await db.user_sessions.delete_many({"user_id": user["user_id"]})
    await db.users.delete_one({"user_id": user["user_id"]})
    response.delete_cookie("session_token", path="/", secure=True, samesite="none")
