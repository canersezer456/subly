"""E-mail discovery: privacy-first analysis of one message's header metadata.

Mailbox access itself lives in lib/discovery/mailbox.py (OAuth, token storage,
fetching). This module only turns (sender, subject, date) into a signal, in memory.

Privacy: the result keeps just the sender domain, the detected signal and the date —
never the subject line, snippet or body. Nothing here logs message content.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from lib import provider_catalog


@dataclass(frozen=True)
class EmailMessageMeta:
    sender: str
    subject: str
    received_at: str  # ISO date
    snippet: str = ""  # adapters leave this empty (metadata-only scopes); never persisted


# Ordered: the first matching signal wins (cancellation beats a generic "subscription" word).
SIGNALS: list[tuple[str, re.Pattern]] = [
    ("cancelled", re.compile(r"(\bcancel+ed\b|\bcancellation\b|iptal edildi|aboneli[gğ]iniz iptal|üyeli[gğ]iniz sona erdi|membership (has )?ended)", re.I)),
    ("trial_ending", re.compile(r"(trial (ends|ending|is ending)|deneme süren(iz)? (bitiyor|sona eriyor)|ücretsiz deneme)", re.I)),
    ("plan_changed", re.compile(r"(plan (changed|updated)|plan(ınız)? değişti|fiyat(ı)? (güncellen|değiş)|price (change|increase))", re.I)),
    ("renewal", re.compile(r"(renew(al|ed|s)?|yenilen(di|ecek|me)|otomatik yenileme)", re.I)),
    ("payment_confirmation", re.compile(r"(payment (received|confirmation|successful)|ödeme(niz)? (alındı|başarılı|onay))", re.I)),
    ("invoice", re.compile(r"(invoice|fatura)", re.I)),
    ("receipt", re.compile(r"(receipt|makbuz|order confirmation|satın alma)", re.I)),
    ("membership", re.compile(r"(membership|üyelik)", re.I)),
    ("subscription", re.compile(r"(subscription|abonelik)", re.I)),
]

# Signals that indicate an ongoing paid subscription (vs. an ended one).
ACTIVE_SIGNALS = {"renewal", "payment_confirmation", "invoice", "receipt", "membership", "subscription", "plan_changed", "trial_ending"}


def classify_email(meta: EmailMessageMeta) -> dict | None:
    """Returns None when the sender is not a known provider (for this subject) or no
    billing signal is present. Otherwise {"provider_ids", "signal", "sender_domain",
    "observed_at"} — deliberately excluding subject/snippet so callers cannot persist
    them by accident."""
    provider_ids = provider_catalog.match_sender(meta.sender, meta.subject)
    if not provider_ids:
        return None
    text = f"{meta.subject}\n{meta.snippet[:500]}"
    signal = next((name for name, pattern in SIGNALS if pattern.search(text)), None)
    if signal is None:
        return None
    domain = meta.sender.strip().lower().rsplit("@", 1)[-1].strip(">").strip()
    return {"provider_ids": provider_ids, "signal": signal, "sender_domain": domain, "observed_at": meta.received_at[:10]}
