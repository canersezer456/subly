import type { ComponentType } from "react";
import {
  SiApple, SiApplemusic, SiAppletv, SiClaude, SiCursor, SiDeezer, SiDropbox, SiEa, SiGithub, SiGithubcopilot,
  SiGoogle, SiGooglegemini, SiGrammarly, SiHbomax, SiIcloud, SiJetbrains, SiMubi, SiNetflix, SiNotion,
  SiPerplexity, SiPlaystation, SiReplit, SiSpotify, SiTidal, SiVercel, SiYoutube, SiYoutubemusic,
} from "@icons-pack/react-simple-icons";
import { Layers3 } from "lucide-react";
import { providerIdForName } from "@/lib/providerCatalog";

type BrandIcon = ComponentType<{ size?: number; color?: string; title?: string }>;

// Named imports only — the package ships thousands of brand icons; a wildcard
// `import *` plus a dynamic string lookup defeats tree-shaking.
//
// Keyed by provider-catalog id (backend/lib/provider_catalog.py). Every icon was
// rendered and checked against the brand before being listed. Deliberately absent,
// because Simple Icons has no mark for them (or only an unrelated one — "SiMax" is
// Max/MSP audio software, not the streaming service): Prime Video, Amazon Prime,
// Disney+, Exxen, Gain, TOD, ChatGPT/OpenAI, Microsoft 365/Copilot, Xbox, Nintendo,
// Adobe, Canva. Those render the neutral placeholder — never a letter, never a
// remote image that could break.
//
// `color: null` = the brand mark is black; draw it in the foreground color so it
// stays visible on the dark theme.
const PROVIDER_ICONS: Record<string, { icon: BrandIcon; color: string | null }> = {
  netflix: { icon: SiNetflix, color: "#E50914" },
  max: { icon: SiHbomax, color: null },
  "apple-tv-plus": { icon: SiAppletv, color: null },
  mubi: { icon: SiMubi, color: null },
  "youtube-premium": { icon: SiYoutube, color: "#FF0033" },
  spotify: { icon: SiSpotify, color: "#1ED760" },
  "apple-music": { icon: SiApplemusic, color: "#FA243C" },
  "youtube-music": { icon: SiYoutubemusic, color: "#FF0000" },
  deezer: { icon: SiDeezer, color: "#A238FF" },
  tidal: { icon: SiTidal, color: null },
  "claude-pro": { icon: SiClaude, color: "#D97757" },
  "claude-max": { icon: SiClaude, color: "#D97757" },
  "google-gemini": { icon: SiGooglegemini, color: "#8E75B2" },
  "perplexity-pro": { icon: SiPerplexity, color: "#1FB8CD" },
  "github-copilot": { icon: SiGithubcopilot, color: null },
  github: { icon: SiGithub, color: null },
  "google-one": { icon: SiGoogle, color: "#4285F4" },
  "icloud-plus": { icon: SiIcloud, color: "#3693F3" },
  "apple-one": { icon: SiApple, color: null },
  dropbox: { icon: SiDropbox, color: "#0061FF" },
  notion: { icon: SiNotion, color: null },
  grammarly: { icon: SiGrammarly, color: "#15C39A" },
  "playstation-plus": { icon: SiPlaystation, color: "#0070D1" },
  "ea-play": { icon: SiEa, color: null },
  jetbrains: { icon: SiJetbrains, color: null },
  vercel: { icon: SiVercel, color: null },
  cursor: { icon: SiCursor, color: null },
  replit: { icon: SiReplit, color: "#F26207" },
};

function surface(color: string | null) {
  if (!color) return "rgba(148,163,184,.14)";
  const n = parseInt(color.slice(1), 16);
  return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},.14)`;
}

export function ProviderMark({ name, providerId, size = "md" }: { name: string; providerId?: string | null; size?: "sm" | "md" | "lg" }) {
  const id = providerId ?? providerIdForName(name);
  const entry = id ? PROVIDER_ICONS[id] : undefined;
  const dimension = size === "lg" ? 58 : size === "sm" ? 36 : 44;
  const iconSize = size === "lg" ? 28 : size === "sm" ? 17 : 21;
  const Icon = entry?.icon;

  return (
    <span
      className="grid shrink-0 place-items-center rounded-[1rem] border border-white/10 text-foreground shadow-lg shadow-slate-950/10"
      style={{ width: dimension, height: dimension, background: surface(entry?.color ?? null), color: entry?.color ?? undefined }}
      data-testid={`provider-mark-${name.toLocaleLowerCase("tr-TR").replaceAll(" ", "-")}`}
      data-provider={id ?? "unknown"}
      role="img"
      aria-label={`${name} amblemi`}
    >
      {Icon ? <Icon size={iconSize} color={entry?.color ?? "currentColor"} title={name} /> : <Layers3 size={iconSize} className="text-muted-foreground" aria-hidden="true" />}
    </span>
  );
}
