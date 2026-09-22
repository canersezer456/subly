import json
import logging
import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from openai import AsyncOpenAI

from lib import finance
from lib.assistant_usage import record_usage
from lib.auth import get_current_user
from lib.budget_guard import check_budget
from lib.circuit_breaker import get_circuit_breaker
from lib.db import db
from models.finance import AssistantMessage, ChatRequest

router = APIRouter(prefix="/assistant", tags=["assistant"])
logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Sen Subly'nin kişisel finans asistanısın. Türkçe, samimi ama net konuşursun.
Kurallar:
- Yalnızca sana verilen kullanıcı verilerine dayanarak cevap ver; veri yoksa bunu açıkça söyle, uydurma.
- Kullanıcı adına finansal karar verme; verileri açıkla, seçenekleri ve tasarruf fırsatlarını sun.
- Tutarları ₺ ile ve binlik ayırıcıyla yaz (örn. ₺18.000). Kısa paragraflar ve gerektiğinde madde işaretleri kullan.
- Cevaplar kısa ve uygulanabilir olsun (en fazla ~180 kelime). Ürün satmaya çalışma.
- Abonelik, fatura ve bütçe verileri "Faturalar" ve "Abonelikler" kategorilerinde gider toplamına otomatik dahildir.
- USD/EUR abonelikler yaklaşık kurla TL'ye çevrilmiştir; bunu gerektiğinde belirt.

Kullanıcının güncel finansal verisi (JSON):
"""


def _sanitize(doc: dict) -> dict:
    return {k: v for k, v in doc.items() if k not in {"user_id", "_id", "created_at", "cancellation_url", "source", "bill_number", "note"}}


async def _build_context(user_id: str) -> str:
    data = await finance.load_user_data(user_id)
    ref = finance.today()
    key = finance.month_key(ref)
    summary = finance.summary(data, ref)
    context = {
        "bugun": ref.isoformat(),
        "ay": summary["month_label"],
        "ozet": {k: summary[k] for k in ("income_total", "expense_total", "remaining", "savings_rate", "last_month_expense", "expense_change_percent", "subscription_monthly", "subscription_yearly", "bills_total", "potential_savings")},
        "kategori_dagilimi": summary["categories"],
        "yaklasan_odemeler_30_gun": summary["upcoming"],
        "butce_kullanimi": summary["budgets"],
        "son_6_ay_trend": summary["trend"],
        "tasarruf_firsatlari": finance.savings_insights(data, key),
        "uyarilar": finance.alerts(data, ref, key),
        "abonelikler": [_sanitize(s) for s in data["subscriptions"]],
        "faturalar": [_sanitize(b) for b in data["bills"]],
        "gelirler": [_sanitize(i) for i in data["incomes"]],
        "bu_ay_harcamalar": [_sanitize(e) for e in data["expenses"] if e["date"][:7] == key],
    }
    return json.dumps(context, ensure_ascii=False, default=str)


@router.get("/history", response_model=list[AssistantMessage])
async def history(user: dict = Depends(get_current_user)):
    docs = await db.assistant_messages.find({"user_id": user["user_id"]}, {"_id": 0}).sort("created_at", 1).to_list(200)
    return [AssistantMessage(**doc) for doc in docs]


@router.delete("/history", status_code=204)
async def clear_history(user: dict = Depends(get_current_user)):
    await db.assistant_messages.delete_many({"user_id": user["user_id"]})


@router.post("/chat")
async def chat(input: ChatRequest, user: dict = Depends(get_current_user)):
    user_id = user["user_id"]

    # Phase 2 budget gate — runs before any context build, message write, or
    # LLM call, so a denied request costs nothing beyond one usage lookup and
    # never touches the OpenAI client.
    budget = await check_budget(db.assistant_usage, user_id=user_id)
    if not budget["allowed"]:
        async def budget_denied_stream():
            yield f"data: {json.dumps({'error': 'Günlük asistan kullanım limitine ulaştın. Lütfen yarın tekrar dene.', 'code': 'budget_exceeded'}, ensure_ascii=False)}\n\n"
            yield "data: {\"done\": true}\n\n"

        return StreamingResponse(
            budget_denied_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    # Phase 3 circuit breaker — runs after the budget gate (a budget denial
    # never touches circuit state) and before any context build, message
    # write, or LLM call.
    breaker = get_circuit_breaker()
    if not await breaker.allow_request():
        async def circuit_open_stream():
            yield f"data: {json.dumps({'error': 'Asistan sağlayıcısı şu anda geçici olarak kullanılamıyor. Lütfen birkaç dakika sonra tekrar dene.', 'code': 'circuit_open'}, ensure_ascii=False)}\n\n"
            yield "data: {\"done\": true}\n\n"

        return StreamingResponse(
            circuit_open_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    context = await _build_context(user_id)
    previous = await db.assistant_messages.find({"user_id": user_id}, {"_id": 0}).sort("created_at", -1).to_list(8)
    transcript = "\n".join(f"{'Kullanıcı' if m['role'] == 'user' else 'Asistan'}: {m['content']}" for m in reversed(previous))
    prompt = (f"Önceki konuşma:\n{transcript}\n\n" if transcript else "") + f"Kullanıcı: {input.message}"

    now = datetime.now(timezone.utc).isoformat()
    await db.assistant_messages.insert_one({"id": str(uuid.uuid4()), "user_id": user_id, "role": "user", "content": input.message, "created_at": now})

    system_message = SYSTEM_PROMPT + context
    provider, model = "openai", "gpt-5.4"
    client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])

    async def event_stream():
        chunks: list[str] = []
        failed = False
        try:
            stream = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt},
                ],
                stream=True,
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta.content if chunk.choices else None
                if delta:
                    chunks.append(delta)
                    yield f"data: {json.dumps({'delta': delta}, ensure_ascii=False)}\n\n"
        except Exception:  # surface provider failures to the UI instead of a silent hang
            failed = True
            logger.exception("assistant stream failed")
            # Never leak raw exception details to the client (could contain provider
            # internals, request payload fragments, or infra info) — a generic,
            # i18n-manageable code is sent instead; full detail stays server-side via
            # logger.exception above.
            yield f"data: {json.dumps({'error': 'Asistan şu anda yanıt veremiyor. Lütfen birkaç dakika sonra tekrar dene.', 'code': 'provider_error'}, ensure_ascii=False)}\n\n"
        # Phase 3 circuit breaker — only this try/except's boundary counts as a
        # provider/LLM failure; nothing before it (auth, budget, breaker gate
        # itself) or after it (message write, usage logging) can reach here.
        if failed:
            await breaker.record_failure()
        else:
            await breaker.record_success()
        content = "".join(chunks).strip()
        if content:
            await db.assistant_messages.insert_one({"id": str(uuid.uuid4()), "user_id": user_id, "role": "assistant", "content": content, "created_at": datetime.now(timezone.utc).isoformat()})
        # Phase 1 usage ledger — additive only, never gates or alters the response above.
        usage_status = "success" if not failed else ("partial" if content else "error")
        await record_usage(db.assistant_usage, user_id=user_id, provider=provider, model=model, input_text=system_message + prompt, output_text=content, status=usage_status)
        yield "data: {\"done\": true}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
