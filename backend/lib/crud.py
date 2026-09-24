"""Generic per-user CRUD router factory: list (optional ?month=YYYY-MM), create, patch, delete."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from lib.auth import get_current_user
from lib.db import db


def crud_router(*, prefix: str, collection: str, create_model, update_model, out_model, date_field: str, sort_desc: bool = True, defaults: dict | None = None) -> APIRouter:
    router = APIRouter(prefix=prefix, tags=[collection])
    coll = db[collection]

    @router.get("", response_model=list[out_model])
    async def list_items(month: str | None = Query(default=None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$"), user: dict = Depends(get_current_user)):
        query: dict = {"user_id": user["user_id"]}
        if month:
            query["month" if collection == "budgets" else date_field] = {"$regex": f"^{month}"}
        docs = await coll.find(query, {"_id": 0}).sort(date_field, -1 if sort_desc else 1).to_list(2000)
        return [out_model(**doc) for doc in docs]

    @router.post("", response_model=out_model, status_code=201)
    async def create_item(input: create_model, user: dict = Depends(get_current_user)):  # type: ignore[valid-type]
        doc = {**(defaults or {}), **input.model_dump()}
        doc.update({"id": str(uuid.uuid4()), "user_id": user["user_id"], "created_at": datetime.now(timezone.utc).isoformat()})
        await coll.insert_one(doc)
        return out_model(**doc)

    @router.patch("/{item_id}", response_model=out_model)
    async def update_item(item_id: str, input: update_model, user: dict = Depends(get_current_user)):  # type: ignore[valid-type]
        changes = input.model_dump(exclude_none=True)
        if not changes:
            raise HTTPException(status_code=400, detail="Güncellenecek alan yok")
        result = await coll.update_one({"id": item_id, "user_id": user["user_id"]}, {"$set": changes})
        if not result.matched_count:
            raise HTTPException(status_code=404, detail="Kayıt bulunamadı")
        doc = await coll.find_one({"id": item_id, "user_id": user["user_id"]}, {"_id": 0})
        return out_model(**doc)

    @router.delete("/{item_id}", status_code=204)
    async def delete_item(item_id: str, user: dict = Depends(get_current_user)):
        result = await coll.delete_one({"id": item_id, "user_id": user["user_id"]})
        if not result.deleted_count:
            raise HTTPException(status_code=404, detail="Kayıt bulunamadı")

    return router
