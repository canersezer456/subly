/**
 * Client-side helpers for the provider catalog. The catalog itself lives in the
 * backend (backend/lib/provider_catalog.py, served by GET /subscriptions/providers);
 * this file only maps free-text names that predate provider ids (legacy rows, deal
 * cards) onto a catalog id for display. Suggestions only: nothing here ever creates
 * an owned subscription.
 */
import type { Provider } from "@/lib/types";

const NAME_TO_ID: Record<string, string> = {
  netflix: "netflix",
  "prime video": "prime-video",
  "amazon prime": "amazon-prime",
  max: "max",
  "hbo max": "max",
  blutv: "max",
  "disney+": "disney-plus",
  "apple tv+": "apple-tv-plus",
  mubi: "mubi",
  exxen: "exxen",
  gain: "gain",
  tod: "tod",
  "bein connect": "tod",
  "youtube premium": "youtube-premium",
  spotify: "spotify",
  "apple music": "apple-music",
  "youtube music": "youtube-music",
  deezer: "deezer",
  tidal: "tidal",
  "chatgpt plus": "chatgpt-plus",
  "chatgpt pro": "chatgpt-pro",
  chatgpt: "chatgpt-plus",
  "claude pro": "claude-pro",
  "claude max": "claude-max",
  claude: "claude-pro",
  gemini: "google-gemini",
  "google gemini": "google-gemini",
  "perplexity pro": "perplexity-pro",
  "github copilot": "github-copilot",
  github: "github",
  "google one": "google-one",
  "icloud+": "icloud-plus",
  icloud: "icloud-plus",
  "apple one": "apple-one",
  "microsoft 365": "microsoft-365",
  dropbox: "dropbox",
  "adobe creative cloud": "adobe-creative-cloud",
  "canva pro": "canva-pro",
  notion: "notion",
  grammarly: "grammarly",
  "playstation plus": "playstation-plus",
  "xbox game pass": "xbox-game-pass",
  "nintendo switch online": "nintendo-switch-online",
  "ea play": "ea-play",
  jetbrains: "jetbrains",
  vercel: "vercel",
  cursor: "cursor",
  replit: "replit",
};

/** Exact (case/whitespace-insensitive) name match only — no fuzzy guessing. */
export function providerIdForName(name: string): string | null {
  const key = name.toLocaleLowerCase("tr-TR").replace(/\s+/g, " ").trim();
  return NAME_TO_ID[key] ?? null;
}

/** Case/diacritic-insensitive search key, mirroring provider_catalog.fold(). */
export function foldSearch(text: string): string {
  return text.replace(/ı/g, "i").replace(/İ/g, "I").normalize("NFKD").replace(/\p{M}/gu, "").toLowerCase().replace(/\s+/g, " ").trim();
}

/** Rank like the backend's search_providers: exact > name prefix > alias prefix > word > substring. */
export function rankProviders(providers: Provider[], query: string): Provider[] {
  const q = foldSearch(query);
  if (!q) return providers;
  const scored: [number, number, Provider][] = [];
  providers.forEach((p, index) => {
    const name = foldSearch(p.name);
    const aliases = p.aliases.map(foldSearch);
    let score: number | null = null;
    if (name === q || aliases.includes(q)) score = 0;
    else if (name.startsWith(q)) score = 1;
    else if (aliases.some((a) => a.startsWith(q))) score = 2;
    else if (name.split(" ").some((w) => w.startsWith(q))) score = 3;
    else if (name.includes(q) || aliases.some((a) => a.includes(q))) score = 4;
    if (score !== null) scored.push([score, index, p]);
  });
  return scored.sort((a, b) => a[0] - b[0] || a[1] - b[1]).map(([, , p]) => p);
}
