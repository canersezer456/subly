"""Shared Mongo handle — import `client`/`db` from here (server.py, routers, seed.py)."""

import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING, DESCENDING, IndexModel

load_dotenv(Path(__file__).parent.parent / ".env")

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

logger = logging.getLogger(__name__)

# One entry per collection: every field a route filters, sorts, or dedupes on. Applied by ensure_indexes() at startup.
INDEXES: dict[str, list[IndexModel]] = {
    "status_checks": [IndexModel([("timestamp", DESCENDING)], name="timestamp_desc")],
    "users": [IndexModel([("email", ASCENDING)], name="email_unique", unique=True)],
    "user_sessions": [IndexModel([("session_token", ASCENDING)], name="session_token_unique", unique=True), IndexModel([("expires_at", ASCENDING)], name="expires_at")],
    "subscriptions": [IndexModel([("user_id", ASCENDING), ("renewal_date", ASCENDING)], name="user_renewal")],
    "subscription_candidates": [IndexModel([("user_id", ASCENDING), ("status", ASCENDING)], name="user_status"), IndexModel([("user_id", ASCENDING), ("dedupe_key", ASCENDING)], name="user_dedupe")],
    "email_connections": [IndexModel([("user_id", ASCENDING), ("provider", ASCENDING)], name="user_provider_unique", unique=True)],
    # expires_at is a datetime: Mongo's TTL monitor removes abandoned OAuth flows.
    "email_oauth_states": [IndexModel([("state", ASCENDING)], name="state_unique", unique=True), IndexModel([("expires_at", ASCENDING)], name="expires_ttl", expireAfterSeconds=0)],
    "incomes": [IndexModel([("user_id", ASCENDING), ("date", DESCENDING)], name="user_date")],
    "expenses": [IndexModel([("user_id", ASCENDING), ("date", DESCENDING)], name="user_date")],
    "bills": [IndexModel([("user_id", ASCENDING), ("due_date", ASCENDING)], name="user_due")],
    "budgets": [IndexModel([("user_id", ASCENDING), ("category", ASCENDING)], name="user_category")],
    "digest_prefs": [IndexModel([("user_id", ASCENDING)], name="user_unique", unique=True), IndexModel([("enabled", ASCENDING), ("weekday", ASCENDING), ("hour", ASCENDING)], name="schedule"), IndexModel([("reminders_enabled", ASCENDING), ("reminder_hour", ASCENDING)], name="reminder_schedule")],
    "assistant_messages": [IndexModel([("user_id", ASCENDING), ("created_at", ASCENDING)], name="user_created")],
    "assistant_usage": [IndexModel([("user_id", ASCENDING), ("created_at", DESCENDING)], name="user_created")],
    "gaming_purchases": [IndexModel([("user_id", ASCENDING), ("date", DESCENDING)], name="user_date"), IndexModel([("expense_id", ASCENDING)], name="expense_id")],
    "gaming_price_overrides": [IndexModel([("user_id", ASCENDING), ("offer_id", ASCENDING)], name="user_offer_unique", unique=True)],
    "gaming_watches": [IndexModel([("user_id", ASCENDING), ("created_at", DESCENDING)], name="user_created"), IndexModel([("user_id", ASCENDING), ("product_id", ASCENDING)], name="user_product")],
    "gaming_price_history": [IndexModel([("user_id", ASCENDING), ("offer_id", ASCENDING), ("changed_at", DESCENDING)], name="user_offer_changed"), IndexModel([("user_id", ASCENDING), ("changed_at", DESCENDING)], name="user_changed")],
}


async def ensure_indexes() -> None:
    for collection, models in INDEXES.items():
        for model in models:  # one at a time so a bad spec skips only itself
            try:
                await db[collection].create_indexes([model])
            except Exception as exc:  # never block boot on an index; the log line names what to fix
                logger.error("ensure_indexes(%s.%s): %s", collection, model.document["name"], exc)
