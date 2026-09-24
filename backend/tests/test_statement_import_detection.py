"""Card-statement detection matrix, CSV import and log redaction."""
import logging
from datetime import date

import pytest
from fastapi.testclient import TestClient

from isolated_store import create_app
from lib import log_redaction, provider_catalog
from lib.db import db
from lib.discovery.importer import parse_statement
from lib.discovery.transactions import Transaction, detect_recurring


# ---- merchant descriptors ----------------------------------------------------------------------

@pytest.mark.parametrize("descriptor, provider", [
    ("OPENAI *CHATGPT SUBSCR", "chatgpt-plus"), ("CHATGPT SUBSCRIPTION", "chatgpt-plus"),
    ("ANTHROPIC* CLAUDE", "claude-pro"), ("CLAUDE.AI SUBSCRIPTION", "claude-pro"),
    ("GOOGLE*GEMINI", "google-gemini"), ("PERPLEXITY AI", "perplexity-pro"),
    ("MICROSOFT*COPILOT PRO", "microsoft-copilot"), ("MSFT*COPILOT", "microsoft-copilot"),
    ("AMAZON PRIME*TR", "amazon-prime"), ("PRIMEVIDEO.COM", "prime-video"), ("AMAZON PRIME VIDEO", "prime-video"),
    ("MAX.COM HELP", "max"), ("HBOMAX", "max"), ("BLUTV ISTANBUL", "max"),
    ("NETFLIX.COM", "netflix"), ("DISNEY PLUS", "disney-plus"), ("DISNEYPLUS TR", "disney-plus"),
    ("SPOTIFY P3A2B1C", "spotify"), ("GOOGLE*YOUTUBE PREMIUM", "youtube-premium"), ("YOUTUBE MUSIC", "youtube-music"),
    ("GOOGLE *GOOGLE ONE", "google-one"), ("PLAYSTATION NETWORK", "playstation-plus"), ("MICROSOFT*XBOX", "xbox-game-pass"),
    ("XBOX GAME PASS", "xbox-game-pass"), ("NINTENDO CD1234", "nintendo-switch-online"), ("ELECTRONIC ARTS", "ea-play"),
    ("EXXEN", "exxen"), ("TOD TV", "tod"), ("BEIN CONNECT", "tod"), ("MUBI", "mubi"), ("DEEZER", "deezer"), ("TIDAL", "tidal"),
    ("DROPBOX*ABC", "dropbox"), ("ADOBE *CREATIVE CLD", "adobe-creative-cloud"), ("CANVA* 12345", "canva-pro"),
    ("NOTION LABS", "notion"), ("GRAMMARLY", "grammarly"), ("JETBRAINS", "jetbrains"), ("VERCEL INC", "vercel"),
    ("CURSOR, ANYSPHERE", "cursor"), ("MICROSOFT*MICROSOFT 365 P", "microsoft-365"),
])
def test_specific_descriptors_map_to_one_product(descriptor, provider):
    match = provider_catalog.match_merchant(descriptor)
    assert match["kind"] == "provider"
    assert match["provider_ids"][0] == provider
    assert provider_catalog.same_family(match["provider_ids"])


@pytest.mark.parametrize("descriptor", ["APPLE.COM/BILL", "ITUNES.COM/BILL", "GOOGLE *PLAY", "GOOGLE", "AMAZON MKTPLACE", "AMZN MKTP TR", "MICROSOFT*STORE", "MSFT *E0400"])
def test_ambiguous_descriptors_never_pick_a_service(descriptor):
    match = provider_catalog.match_merchant(descriptor)
    assert match["kind"] == "ambiguous" and len(match["provider_ids"]) > 1
    [draft] = detect_recurring([Transaction(date(2026, 1, 5), descriptor, 49.99), Transaction(date(2026, 2, 5), descriptor, 49.99), Transaction(date(2026, 3, 5), descriptor, 49.99)], evidence_type="manual_import", evidence_source="import", today=date(2026, 3, 10))
    assert draft["provider_id"] is None and draft["ambiguous"] and draft["confidence"] < 0.5  # even when perfectly monthly


@pytest.mark.parametrize("descriptor", ["TOPSNACK BUFE", "CANVAS SANAT", "MAXIMUM MARKET", "NETFLIXX FAKE SHOP", "BIM A.S.", "SHELL PETROL"])
def test_word_boundaries_prevent_false_matches(descriptor):
    assert provider_catalog.match_merchant(descriptor)["kind"] == "unknown"


def test_store_descriptor_single_charge_is_weak_evidence():
    [one] = detect_recurring([Transaction(date(2026, 3, 1), "PLAYSTATION NETWORK", 899)], evidence_type="manual_import", evidence_source="import", today=date(2026, 3, 10))
    assert one["confidence"] < 0.5  # likely a game purchase, not PS Plus
    monthly = detect_recurring([Transaction(date(2026, m, 1), "PLAYSTATION NETWORK", 199) for m in (1, 2, 3)], evidence_type="manual_import", evidence_source="import", today=date(2026, 3, 10))[0]
    assert monthly["confidence"] >= 0.75 and monthly["billing_cycle"] == "monthly"


# ---- CSV import ------------------------------------------------------------------------------------

def test_turkish_bank_csv_with_quotes_debit_and_credit_columns():
    csv_text = (
        "﻿İşlem Tarihi;Açıklama;Borç;Alacak;Para Birimi\n"
        '05.01.2026;"NETFLIX.COM; ISTANBUL";"229,99";;TRY\n'
        '06.01.2026;"MAAŞ ÖDEMESİ";;"45.000,00";TRY\n'  # money in: skipped
        '07.01.2026;"OPENAI *CHATGPT";"20,00";;USD\n'
        "bozuk;satır;x;;\n"
    )
    txns, skipped = parse_statement(csv_text)
    assert [(t.date.isoformat(), t.description, t.amount, t.currency) for t in txns] == [
        ("2026-01-05", "NETFLIX.COM; ISTANBUL", 229.99, "TRY"),
        ("2026-01-07", "OPENAI *CHATGPT", 20.0, "USD"),
    ]
    assert skipped == 2


def test_english_csv_with_signed_amount_and_comma_delimiter():
    txns, skipped = parse_statement('Date,Description,Amount\n2026-02-01,"SPOTIFY, STOCKHOLM","-9.99 USD"\n2026-02-03,Refund,"12.00"\n')
    assert [(t.description, t.amount, t.currency) for t in txns] == [("SPOTIFY, STOCKHOLM", 9.99, "USD"), ("Refund", 12.0, "TRY")]
    assert skipped == 0


def test_loose_lines_still_work_without_header():
    txns, skipped = parse_statement("2026-01-05;NETFLIX.COM;229,99\n05.02.2026 NETFLIX.COM 229,99 TL\nnot a line")
    assert len(txns) == 2 and skipped == 1


@pytest.fixture
def client():
    for collection in db.collections.values():
        collection.docs.clear()
    with TestClient(create_app(), base_url="https://testserver") as c:
        assert c.post("/api/auth/register", json={"email": "csv@example.com", "name": "csv", "password": "TestPass123!"}).status_code == 200
        yield c


def test_csv_import_endpoint_creates_candidates_only_and_stores_no_raw_rows(client, caplog):
    caplog.set_level(logging.DEBUG)
    text = "Tarih;Açıklama;Tutar\n" + "\n".join(f"2026-0{m}-05;\"NETFLIX.COM KART 4821 ISTANBUL\";\"229,99\"" for m in (1, 2, 3))
    body = client.post("/api/subscriptions/candidates/import", json={"text": text}).json()
    assert body["parsed_transactions"] == 3 and body["created"] == 1
    assert client.get("/api/subscriptions").json() == []
    stored = str(db["subscription_candidates"].docs)
    assert "4821" not in stored and "ISTANBUL" not in stored
    assert "4821" not in caplog.text


# ---- log redaction ---------------------------------------------------------------------------------

def test_access_log_lines_have_oauth_params_redacted():
    record = logging.LogRecord("uvicorn.access", logging.INFO, __file__, 1, '%s - "%s %s HTTP/%s" %d', ("1.2.3.4:5", "GET", "/api/subscriptions/discovery/email/gmail/callback?code=4/0AbcDEF&state=xyz123&scope=gmail", "1.1", 303), None)
    log_redaction.RedactOAuthParams().filter(record)
    message = record.getMessage()
    assert "4/0AbcDEF" not in message and "xyz123" not in message
    assert "code=[redacted]" in message and "scope=gmail" in message
