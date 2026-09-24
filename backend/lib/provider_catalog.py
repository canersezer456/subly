"""Central subscription-provider catalog.

This is reference data only. Nothing in here is ever written into a user's
`subscriptions` collection on its own: selecting a provider pre-fills a form,
and discovery only produces *candidates* the user must accept.

Per provider:
- `id`               canonical id (stable; stored on subscriptions/candidates as `provider_id`)
- `name`, `category` display name and catalog category (see CATEGORY_TO_SUBSCRIPTION)
- `aliases`          extra search terms (former brand names, common spellings)
- `plans`            known plan names only — never prices
- `manage_url`       official account/billing page where the user manages or cancels
- `merchant_patterns` card-statement descriptor fragments (upper-case) that identify this provider
- `email_domains`    sender domains that send this provider's receipts/renewal mails
- `default_currency` only where the provider bills Turkish users in one currency; else None
- `pricing`          always {"status": "not_tracked"}: Subly does not store list prices,
                     because they change and differ per country/plan. The user enters what
                     they actually pay.
- `note`             optional clarification (e.g. rebrands)
- `email_keywords`   subject keywords that pin a message to this provider; with
                     `email_keywords_required`, a sender domain alone is not enough
                     (amazon.com.tr also sends shopping orders, google.com security mail…)
- `one_off_purchases` the descriptor is also used for one-off store purchases
                     (PlayStation Store, Xbox, Nintendo eShop), so a single charge is weak evidence
- `family`           plans of one product share a family (ChatGPT Plus/Pro); providers in
                     different families behind one sender/merchant are ambiguous

Ambiguous merchants (e.g. APPLE.COM/BILL, GOOGLE, AMAZON, MICROSOFT) are listed in
AMBIGUOUS_MERCHANTS: they map to *several* possible providers and must never be
treated as a confident match.
"""

from __future__ import annotations

import re
import unicodedata

# Catalog category -> the Turkish category value the subscriptions UI already stores.
CATEGORY_TO_SUBSCRIPTION = {
    "streaming": "Eğlence",
    "music": "Müzik",
    "ai": "Yapay Zekâ",
    "cloud": "Bulut",
    "productivity": "İş / Yazılım",
    "gaming": "Oyun",
    "developer": "İş / Yazılım",
    "sports": "Spor",
    "bundle": "Diğer",
}

CATEGORY_LABELS_TR = {
    "streaming": "video yayın",
    "music": "müzik",
    "ai": "yapay zekâ",
    "cloud": "bulut depolama",
    "productivity": "üretkenlik",
    "gaming": "oyun",
    "developer": "geliştirici",
    "sports": "spor yayını",
    "bundle": "paket üyelik",
}

_NOT_TRACKED = {"status": "not_tracked"}


def _p(id: str, name: str, category: str, manage_url: str, *, aliases=(), plans=(), merchants=(), domains=(), currency=None, note=None, family=None, email_keywords=(), keywords_required=False, store=False) -> dict:
    return {
        "id": id,
        "family": family or id,
        "name": name,
        "category": category,
        "aliases": list(aliases),
        "plans": list(plans),
        "manage_url": manage_url,
        "merchant_patterns": list(merchants),
        "email_domains": list(domains),
        "email_keywords": list(email_keywords),
        "email_keywords_required": keywords_required,
        "one_off_purchases": store,
        "default_currency": currency,
        "pricing": dict(_NOT_TRACKED),
        "note": note,
    }


PROVIDERS: list[dict] = [
    # --- Streaming ---------------------------------------------------------
    _p("netflix", "Netflix", "streaming", "https://www.netflix.com/account", plans=("Temel", "Standart", "Özel"), merchants=("NETFLIX",), domains=("netflix.com", "mailer.netflix.com"), currency="TRY"),
    _p("prime-video", "Prime Video", "streaming", "https://www.primevideo.com/settings", aliases=("amazon prime video", "prime"), merchants=("PRIME VIDEO", "PRIMEVIDEO", "AMAZON PRIME VIDEO"), domains=("primevideo.com",), note="Türkiye'de Prime Video çoğunlukla Amazon Prime üyeliğinin parçasıdır.", email_keywords=("prime video",)),
    _p("max", "Max", "streaming", "https://www.max.com/account", aliases=("hbo max", "hbo", "blutv", "blu tv"), plans=("Standart", "Premium"), merchants=("MAX.COM", "HBO MAX", "HBOMAX", "BLUTV", "BLU TV"), domains=("max.com", "hbomax.com", "blutv.com"), note="BluTV, 2024'te Türkiye'de Max olarak yeniden markalandı; eski BluTV kayıtları Max altında yönetilir."),
    _p("disney-plus", "Disney+", "streaming", "https://www.disneyplus.com/account", aliases=("disney plus", "disneyplus"), merchants=("DISNEY PLUS", "DISNEYPLUS", "DISNEY+"), domains=("disneyplus.com", "mail.disneyplus.com")),
    _p("apple-tv-plus", "Apple TV+", "streaming", "https://tv.apple.com/settings", aliases=("apple tv", "appletv"), domains=("apple.com", "email.apple.com"), email_keywords=("apple tv",)),
    _p("mubi", "MUBI", "streaming", "https://mubi.com/account", merchants=("MUBI",), domains=("mubi.com",)),
    _p("exxen", "Exxen", "streaming", "https://www.exxen.com/tr/profile", plans=("Exxen", "ExxenSpor"), merchants=("EXXEN",), domains=("exxen.com",), currency="TRY"),
    _p("gain", "Gain", "streaming", "https://www.gain.tv/", merchants=("GAIN MEDYA", "GAIN.TV", "GAINTV"), domains=("gain.tv",), currency="TRY"),
    _p("tod", "TOD", "sports", "https://www.tod.tv/", aliases=("bein connect", "beinconnect", "tod tv"), merchants=("TOD TV", "TOD.TV", "BEIN CONNECT", "DIGITURK"), domains=("tod.tv", "beinconnect.com.tr", "digiturk.com.tr"), currency="TRY", note="beIN CONNECT, 2023'te TOD olarak yeniden markalandı."),
    _p("youtube-premium", "YouTube Premium", "streaming", "https://www.youtube.com/paid_memberships", aliases=("youtube",), plans=("Bireysel", "Aile", "Öğrenci"), merchants=("YOUTUBE PREMIUM", "YOUTUBEPREMIUM", "GOOGLE*YOUTUBE", "GOOGLE YOUTUBE"), domains=("youtube.com", "google.com"), email_keywords=("youtube premium", "premium"), keywords_required=True),
    # --- Music ------------------------------------------------------------
    _p("spotify", "Spotify", "music", "https://www.spotify.com/account/subscription/", plans=("Premium Bireysel", "Premium Duo", "Premium Aile", "Premium Öğrenci"), merchants=("SPOTIFY",), domains=("spotify.com",)),
    _p("apple-music", "Apple Music", "music", "https://music.apple.com/account/settings", domains=("apple.com", "email.apple.com"), email_keywords=("apple music",)),
    _p("youtube-music", "YouTube Music", "music", "https://www.youtube.com/paid_memberships", merchants=("YOUTUBE MUSIC", "GOOGLE*YOUTUBE MUSIC"), domains=("youtube.com", "google.com"), email_keywords=("youtube music", "music premium"), keywords_required=True),
    _p("deezer", "Deezer", "music", "https://www.deezer.com/account/subscription", merchants=("DEEZER",), domains=("deezer.com",)),
    _p("tidal", "TIDAL", "music", "https://account.tidal.com/subscription", merchants=("TIDAL",), domains=("tidal.com",)),
    # --- AI ---------------------------------------------------------------
    _p("chatgpt-plus", "ChatGPT Plus", "ai", "https://chatgpt.com/#settings/Subscription", aliases=("chatgpt", "openai", "gpt"), plans=("Plus",), merchants=("OPENAI", "CHATGPT"), domains=("openai.com", "tm.openai.com"), family="chatgpt"),
    _p("chatgpt-pro", "ChatGPT Pro", "ai", "https://chatgpt.com/#settings/Subscription", aliases=("chatgpt", "openai", "gpt"), plans=("Pro",), merchants=("OPENAI", "CHATGPT"), domains=("openai.com", "tm.openai.com"), family="chatgpt"),
    _p("claude-pro", "Claude Pro", "ai", "https://claude.ai/settings/billing", aliases=("claude", "anthropic"), plans=("Pro",), merchants=("ANTHROPIC", "CLAUDE.AI", "CLAUDE AI"), domains=("anthropic.com", "mail.anthropic.com"), family="claude"),
    _p("claude-max", "Claude Max", "ai", "https://claude.ai/settings/billing", aliases=("claude", "anthropic"), plans=("Max 5x", "Max 20x"), merchants=("ANTHROPIC", "CLAUDE.AI", "CLAUDE AI"), domains=("anthropic.com", "mail.anthropic.com"), family="claude"),
    _p("google-gemini", "Google Gemini", "ai", "https://one.google.com/settings", aliases=("gemini", "gemini advanced", "google ai pro"), note="Gemini'nin ücretli planları Google One üzerinden faturalanır.", merchants=("GOOGLE*GEMINI",), domains=("google.com",), email_keywords=("gemini", "google ai"), keywords_required=True),
    _p("perplexity-pro", "Perplexity Pro", "ai", "https://www.perplexity.ai/settings/account", aliases=("perplexity",), merchants=("PERPLEXITY",), domains=("perplexity.ai",)),
    _p("microsoft-copilot", "Microsoft Copilot Pro", "ai", "https://account.microsoft.com/services", aliases=("copilot", "copilot pro"), merchants=("MICROSOFT*COPILOT", "MSFT*COPILOT", "COPILOT PRO"), domains=("microsoft.com", "email.microsoft.com"), email_keywords=("copilot",), keywords_required=True),
    _p("github-copilot", "GitHub Copilot", "developer", "https://github.com/settings/copilot", aliases=("copilot",), plans=("Pro", "Pro+"), merchants=("GITHUB", "GH COPILOT"), domains=("github.com",), email_keywords=("copilot",), keywords_required=True),
    # --- Cloud / productivity -------------------------------------------
    _p("google-one", "Google One", "cloud", "https://one.google.com/settings", aliases=("google drive", "google storage"), plans=("100 GB", "200 GB", "2 TB"), merchants=("GOOGLE*GOOGLE ONE", "GOOGLE ONE", "GOOGLE STORAGE"), domains=("google.com",), email_keywords=("google one", "depolama", "storage"), keywords_required=True),
    _p("icloud-plus", "iCloud+", "cloud", "https://support.apple.com/billing", aliases=("icloud", "apple icloud"), plans=("50 GB", "200 GB", "2 TB"), domains=("apple.com", "email.apple.com"), email_keywords=("icloud",)),
    _p("apple-one", "Apple One", "bundle", "https://support.apple.com/billing", aliases=("apple",), plans=("Bireysel", "Aile"), domains=("apple.com", "email.apple.com"), email_keywords=("apple one",)),
    _p("microsoft-365", "Microsoft 365", "productivity", "https://account.microsoft.com/services", aliases=("office 365", "office", "m365"), plans=("Personal", "Family"), merchants=("MICROSOFT*365", "MICROSOFT 365", "MSFT*365"), domains=("microsoft.com", "email.microsoft.com"), email_keywords=("microsoft 365", "office 365"), keywords_required=True),
    _p("dropbox", "Dropbox", "cloud", "https://www.dropbox.com/account/plan", plans=("Plus", "Essentials"), merchants=("DROPBOX",), domains=("dropbox.com", "dropboxmail.com")),
    _p("adobe-creative-cloud", "Adobe Creative Cloud", "productivity", "https://account.adobe.com/plans", aliases=("adobe", "photoshop", "lightroom", "acrobat"), plans=("Tüm Uygulamalar", "Photography", "Tek uygulama", "Acrobat Pro"), merchants=("ADOBE",), domains=("adobe.com", "mail.adobe.com")),
    _p("canva-pro", "Canva Pro", "productivity", "https://www.canva.com/settings/billing-and-teams", aliases=("canva",), merchants=("CANVA",), domains=("canva.com",)),
    _p("notion", "Notion", "productivity", "https://www.notion.so/profile/billing", plans=("Plus", "Business"), merchants=("NOTION",), domains=("notion.so", "mail.notion.so")),
    _p("grammarly", "Grammarly", "productivity", "https://account.grammarly.com/subscription", plans=("Pro",), merchants=("GRAMMARLY",), domains=("grammarly.com",)),
    _p("amazon-prime", "Amazon Prime", "bundle", "https://www.amazon.com.tr/gp/primecentral", aliases=("prime", "amazon"), merchants=("AMAZON PRIME", "AMZN PRIME", "PRIME UYELIK"), domains=("amazon.com.tr", "amazon.com"), currency="TRY", email_keywords=("prime",), keywords_required=True),
    # --- Gaming -----------------------------------------------------------
    _p("playstation-plus", "PlayStation Plus", "gaming", "https://www.playstation.com/acct/management", aliases=("ps plus", "psn"), plans=("Essential", "Extra", "Deluxe"), merchants=("PLAYSTATION", "SONY INTERACTIVE", "PSN"), domains=("playstation.com", "email.playstation.com"), email_keywords=("playstation plus", "ps plus"), keywords_required=True, store=True),
    _p("xbox-game-pass", "Xbox Game Pass", "gaming", "https://account.microsoft.com/services", aliases=("game pass", "xbox"), plans=("Core", "Standard", "Ultimate", "PC Game Pass"), merchants=("XBOX", "MICROSOFT*XBOX"), domains=("xbox.com", "microsoft.com"), email_keywords=("game pass",), keywords_required=True, store=True),
    _p("nintendo-switch-online", "Nintendo Switch Online", "gaming", "https://accounts.nintendo.com/", aliases=("nintendo", "switch online"), plans=("Bireysel", "Aile", "Genişletme Paketi"), merchants=("NINTENDO",), domains=("nintendo.com", "accounts.nintendo.com"), email_keywords=("switch online",), keywords_required=True, store=True),
    _p("ea-play", "EA Play", "gaming", "https://myaccount.ea.com/cp-ui/subscription/index", aliases=("ea", "electronic arts"), plans=("EA Play", "EA Play Pro"), merchants=("ELECTRONIC ARTS", "EA *", "EA.COM"), domains=("ea.com",), email_keywords=("ea play",), keywords_required=True, store=True),
    # --- Developer --------------------------------------------------------
    _p("github", "GitHub", "developer", "https://github.com/settings/billing", plans=("Pro", "Team"), merchants=("GITHUB",), domains=("github.com",), email_keywords=("github pro", "github team"), keywords_required=True),
    _p("jetbrains", "JetBrains", "developer", "https://account.jetbrains.com/licenses", aliases=("intellij", "pycharm", "webstorm"), plans=("All Products Pack", "Tek IDE"), merchants=("JETBRAINS",), domains=("jetbrains.com",)),
    _p("vercel", "Vercel", "developer", "https://vercel.com/account/billing", plans=("Pro",), merchants=("VERCEL",), domains=("vercel.com",)),
    _p("cursor", "Cursor", "developer", "https://cursor.com/settings", plans=("Pro", "Business"), merchants=("CURSOR", "ANYSPHERE"), domains=("cursor.com", "cursor.sh")),
    _p("replit", "Replit", "developer", "https://replit.com/account", plans=("Core",), merchants=("REPLIT",), domains=("replit.com",)),
]

PROVIDERS_BY_ID: dict[str, dict] = {p["id"]: p for p in PROVIDERS}

# Descriptors that bill for several different services. A match here is only ever
# "inceleme gerekli" with a list of possibilities, never a confident provider.
AMBIGUOUS_MERCHANTS: list[dict] = [
    {"pattern": "APPLE.COM/BILL", "label": "Apple (App Store / iCloud / Apple Music / Apple TV+)", "providers": ["icloud-plus", "apple-music", "apple-tv-plus", "apple-one"]},
    {"pattern": "APPLE.COM", "label": "Apple", "providers": ["icloud-plus", "apple-music", "apple-tv-plus", "apple-one"]},
    {"pattern": "ITUNES", "label": "Apple (iTunes)", "providers": ["icloud-plus", "apple-music", "apple-tv-plus", "apple-one"]},
    {"pattern": "GOOGLE", "label": "Google (Play / One / YouTube)", "providers": ["google-one", "youtube-premium", "youtube-music", "google-gemini"]},
    {"pattern": "AMAZON", "label": "Amazon", "providers": ["amazon-prime", "prime-video"]},
    {"pattern": "AMZN", "label": "Amazon", "providers": ["amazon-prime", "prime-video"]},
    {"pattern": "MICROSOFT", "label": "Microsoft", "providers": ["microsoft-365", "xbox-game-pass", "microsoft-copilot"]},
    {"pattern": "MSFT", "label": "Microsoft", "providers": ["microsoft-365", "xbox-game-pass", "microsoft-copilot"]},
]


def fold(text: str) -> str:
    """Case/diacritic-insensitive key: 'Exxen Spor' / 'EXXENSPOR' / 'exxenspor' all compare equal-ish."""
    text = unicodedata.normalize("NFKD", text.replace("ı", "i").replace("İ", "I"))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", text).strip().lower()


def get_provider(provider_id: str | None) -> dict | None:
    return PROVIDERS_BY_ID.get(provider_id or "")


def public_provider(p: dict) -> dict:
    """Shape returned by the API (drops nothing sensitive — it is all reference data)."""
    return {**p, "subscription_category": CATEGORY_TO_SUBSCRIPTION.get(p["category"], "Diğer")}


def search_providers(query: str, limit: int = 20) -> list[dict]:
    """Rank by name prefix > alias prefix > word match > substring. Empty query -> whole catalog."""
    q = fold(query or "")
    if not q:
        return [public_provider(p) for p in PROVIDERS][:limit]
    scored: list[tuple[int, int, dict]] = []
    for index, p in enumerate(PROVIDERS):
        name = fold(p["name"])
        aliases = [fold(a) for a in p["aliases"]]
        if name == q or q in aliases:
            score = 0
        elif name.startswith(q):
            score = 1
        elif any(a.startswith(q) for a in aliases):
            score = 2
        elif any(word.startswith(q) for word in name.split()):
            score = 3
        elif q in name or any(q in a for a in aliases):
            score = 4
        else:
            continue
        scored.append((score, index, p))
    scored.sort(key=lambda item: (item[0], item[1]))
    return [public_provider(p) for _, _, p in scored[:limit]]


def guess_provider_by_name(name: str) -> dict | None:
    """Exact (folded) name/alias match only — used to label legacy rows, never to create data."""
    key = fold(name or "")
    if not key:
        return None
    for p in PROVIDERS:
        if fold(p["name"]) == key:
            return p
    by_alias = [p for p in PROVIDERS if key in (fold(a) for a in p["aliases"])]
    # "ChatGPT" -> ChatGPT Plus/Pro are one product; "prime" -> Prime Video/Amazon Prime are not.
    if by_alias and same_family([p["id"] for p in by_alias]):
        return by_alias[0]
    return None


def _descriptor_key(text: str) -> str:
    return re.sub(r"\s+", " ", fold(text).upper())


def _contains(key: str, pattern: str) -> bool:
    """Substring match that respects word edges where the pattern has letters/digits,
    so "PSN" does not fire inside "TOPSNACK" and "CANVA" not inside "CANVAS"."""
    left = r"(?<![A-Z0-9])" if pattern[:1].isalnum() else ""
    right = r"(?![A-Z0-9])" if pattern[-1:].isalnum() else ""
    return re.search(left + re.escape(pattern) + right, key) is not None


def match_merchant(descriptor: str) -> dict:
    """Normalize a card-statement descriptor.

    Returns {"kind": "provider", "provider_ids": [...], "matched": pattern}
         or {"kind": "ambiguous", "provider_ids": [...], "label": ..., "matched": pattern}
         or {"kind": "unknown"}.

    Specific patterns win over ambiguous ones ("GOOGLE*YOUTUBE" -> YouTube Premium,
    bare "GOOGLE" -> ambiguous). Several providers can share a pattern (OPENAI ->
    ChatGPT Plus / ChatGPT Pro); that is still returned as kind="provider" with every
    candidate id so the caller can ask the user which plan it is.
    """
    key = _descriptor_key(descriptor)
    if not key:
        return {"kind": "unknown"}
    best: tuple[int, str, list[str]] | None = None
    for p in PROVIDERS:
        for pattern in p["merchant_patterns"]:
            pat = _descriptor_key(pattern)
            if pat and _contains(key, pat):
                if best is None or len(pat) > best[0]:
                    best = (len(pat), pat, [p["id"]])
                elif len(pat) == best[0] and p["id"] not in best[2]:
                    best[2].append(p["id"])
    if best:
        return {"kind": "provider", "provider_ids": best[2], "matched": best[1]}
    for amb in AMBIGUOUS_MERCHANTS:
        pat = _descriptor_key(amb["pattern"])
        if _contains(key, pat):
            return {"kind": "ambiguous", "provider_ids": list(amb["providers"]), "label": amb["label"], "matched": pat}
    return {"kind": "unknown"}


def match_sender(sender: str, subject: str | None = None) -> list[str]:
    """Provider ids for a sender address (or bare domain), narrowed by the subject.

    - providers whose keyword appears in the subject win outright;
    - otherwise only providers that do not *require* a keyword remain — so an
      amazon.com.tr shopping order never becomes "Amazon Prime", while a generic
      "Your receipt from Apple" stays ambiguous across the Apple services.
    The subject is only inspected in memory.
    """
    address = (sender or "").strip().lower()
    domain = address.rsplit("@", 1)[-1].strip(">").strip()
    if not domain:
        return []
    by_domain = [p for p in PROVIDERS if any(domain == d or domain.endswith("." + d) for d in p["email_domains"])]
    text = fold(subject or "")
    keyworded = [p for p in by_domain if any(fold(k) in text for k in p["email_keywords"])]
    if keyworded:
        return [p["id"] for p in keyworded]
    return [p["id"] for p in by_domain if not p["email_keywords_required"]]


def same_family(provider_ids: list[str]) -> bool:
    """True when every id is a plan of one product (e.g. ChatGPT Plus / Pro)."""
    families = {PROVIDERS_BY_ID[pid]["family"] for pid in provider_ids if pid in PROVIDERS_BY_ID}
    return len(families) <= 1
