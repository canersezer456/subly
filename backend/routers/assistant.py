import json
import logging
import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from lib import finance
from lib.assistant_usage import record_usage
from lib.auth import get_current_user
from lib.budget_guard import check_budget
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
    # never touches emergentintegrations.
    budget = await check_budget(db.assistant_usage, user_id=user_id)
    if not budget["allowed"]:
        async def budget_denied_stream():
            yield f"data: {json.dumps({'error': 'Günlük asistan kullanım limitine ulaştın. Lütfen yarın tekrar dene.'}, ensure_ascii=False)}\n\n"
            yield "data: {\"done\": true}\n\n"

        return StreamingResponse(
            budget_denied_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    from emergentintegrations.llm.chat import LlmChat, StreamDone, TextDelta, UserMessage

    context = await _build_context(user_id)
    previous = await db.assistant_messages.find({"user_id": user_id}, {"_id": 0}).sort("created_at", -1).to_list(8)
    transcript = "\n".join(f"{'Kullanıcı' if m['role'] == 'user' else 'Asistan'}: {m['content']}" for m in reversed(previous))
    prompt = (f"Önceki konuşma:\n{transcript}\n\n" if transcript else "") + f"Kullanıcı: {input.message}"

    now = datetime.now(timezone.utc).isoformat()
    await db.assistant_messages.insert_one({"id": str(uuid.uuid4()), "user_id": user_id, "role": "user", "content": input.message, "created_at": now})

    system_message = SYSTEM_PROMPT + context
    provider, model = "openai", "gpt-5.4"
    llm = LlmChat(api_key=os.environ["EMERGENT_LLM_KEY"], session_id=f"subly-{user_id}-{uuid.uuid4().hex[:8]}", system_message=system_message).with_model(provider, model)

    async def event_stream():
        chunks: list[str] = []
        failed = False
        try:
            async for event in llm.stream_message(UserMessage(text=prompt)):
                if isinstance(event, TextDelta):
                    chunks.append(event.content)
                    yield f"data: {json.dumps({'delta': event.content}, ensure_ascii=False)}\n\n"
                elif isinstance(event, StreamDone):
                    break
        except Exception as exc:  # surface provider failures to the UI instead of a silent hang
            failed = True
            logger.exception("assistant stream failed")
            yield f"data: {json.dumps({'error': 'Asistan şu anda yanıt veremiyor: ' + str(exc)[:120]}, ensure_ascii=False)}\n\n"
        content = "".join(chunks).strip()
        if content:
            await db.assistant_messages.insert_one({"id": str(uuid.uuid4()), "user_id": user_id, "role": "assistant", "content": content, "created_at": datetime.now(timezone.utc).isoformat()})
        # Phase 1 usage ledger — additive only, never gates or alters the response above.
        usage_status = "success" if not failed else ("partial" if content else "error")
        await record_usage(db.assistant_usage, user_id=user_id, provider=provider, model=model, input_text=system_message + prompt, output_text=content, status=usage_status)
        yield "data: {\"done\": true}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
