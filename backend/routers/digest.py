from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from lib import digest, finance
from lib.auth import get_current_user
from lib.db import db

router = APIRouter(prefix="/digest", tags=["digest"])


class DigestPreferencesUpdate(BaseModel):
    enabled: bool
    weekday: int = Field(ge=0, le=6)  # 0 = Pazartesi
    hour: int = Field(ge=0, le=23)
    reminders_enabled: bool = False
    reminder_hour: int = Field(default=8, ge=0, le=23)


class DigestPreferences(DigestPreferencesUpdate):
    last_sent_at: str | None = None
    last_reminder_date: str | None = None


class ReminderPreview(BaseModel):
    due_count: int
    total: float
    subject: str | None = None
    html: str | None = None


class ReminderSendResult(BaseModel):
    sent_to: str
    email_id: str | None
    due_count: int


class DigestPreview(BaseModel):
    subject: str
    html: str


class DigestSendResult(BaseModel):
    sent_to: str
    email_id: str | None


def _origin(request: Request) -> str:
    origin = request.headers.get("origin") or ""
    if not origin and (referer := request.headers.get("referer")):
        origin = "/".join(referer.split("/")[:3])
    return origin if origin.startswith("https://") else ""


@router.get("/preferences", response_model=DigestPreferences)
async def get_preferences(user: dict = Depends(get_current_user)):
    return await digest.get_prefs(user["user_id"])


@router.put("/preferences", response_model=DigestPreferences)
async def update_preferences(input: DigestPreferencesUpdate, request: Request, user: dict = Depends(get_current_user)):
    changes = {**input.model_dump(), "user_id": user["user_id"]}
    if origin := _origin(request):
        changes["origin"] = origin  # remembered so scheduled emails can link back to the app
    await db.digest_prefs.update_one({"user_id": user["user_id"]}, {"$set": changes}, upsert=True)
    return await digest.get_prefs(user["user_id"])


@router.get("/preview", response_model=DigestPreview)
async def preview(request: Request, user: dict = Depends(get_current_user)):
    data = await finance.load_user_data(user["user_id"])
    subject, html = digest.build_digest(user, data, _origin(request))
    return {"subject": subject, "html": html}


@router.post("/send-now", response_model=DigestSendResult)
async def send_now(request: Request, user: dict = Depends(get_current_user)):
    # Recipient is always the authenticated user's own stored address (G4); one send per 10 minutes.
    prefs = await digest.get_prefs(user["user_id"])
    if prefs.get("last_sent_at") and datetime.fromisoformat(prefs["last_sent_at"]) > datetime.now(timezone.utc) - timedelta(minutes=10):
        raise HTTPException(status_code=429, detail="Az önce bir özet gönderildi; 10 dakika sonra tekrar dene")
    email_id = await digest.send_digest(user, _origin(request))
    return {"sent_to": user["email"], "email_id": email_id}


@router.get("/reminder-preview", response_model=ReminderPreview)
async def reminder_preview(request: Request, user: dict = Depends(get_current_user)):
    data = await finance.load_user_data(user["user_id"])
    items = digest.due_today(data)
    total = round(sum(finance.to_try(i["amount"], i["currency"]) for i in items), 2)
    if not items:
        return {"due_count": 0, "total": 0.0}
    subject, html = digest.build_reminder(user, items, _origin(request))
    return {"due_count": len(items), "total": total, "subject": subject, "html": html}


@router.post("/send-reminder-now", response_model=ReminderSendResult)
async def send_reminder_now(request: Request, user: dict = Depends(get_current_user)):
    # Recipient is the authenticated user's own stored address (G4); at most one manual reminder per day.
    prefs = await digest.get_prefs(user["user_id"])
    if prefs.get("last_reminder_date") == finance.today().isoformat():
        raise HTTPException(status_code=429, detail="Bugünkü hatırlatma zaten gönderildi")
    email_id, count = await digest.send_reminder(user, _origin(request))
    if not count:
        raise HTTPException(status_code=409, detail="Bugün vadesi gelen ödeme yok; hatırlatma gönderilmedi")
    return {"sent_to": user["email"], "email_id": email_id, "due_count": count}
