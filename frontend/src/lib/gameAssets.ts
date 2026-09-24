/**
 * Single source of truth for Gaming artwork, keyed by catalog slug
 * (backend/lib/gaming_catalog.py `GAMES[].slug`).
 *
 * The backend's `icon_url` values are hotlinked upload.wikimedia.org thumbnail
 * URLs that no longer resolve, so the UI never reads them. Every asset here is
 * a file bundled under `public/gaming/`, so rendering does not depend on any
 * third-party host staying up or keeping a path stable.
 *
 * - `logo`  – square mark for lists/tiles (`public/gaming/logos/`).
 * - `cover` – landscape artwork for the game hero and deal cards
 *             (`public/gaming/covers/`). Only set where genuine official
 *             artwork for that exact game was verified; absent otherwise.
 *
 * Sources (all verified to show the named game/platform):
 * - Official App Store app icons / store screenshots published by each game's
 *   own publisher (PUBG Mobile, MLBB, Roblox, Genshin Impact, CoD Mobile,
 *   Clash of Clans, Clash Royale, Brawl Stars, Minecraft, Xbox, Steam).
 * - Simple Icons brand paths (CC0) on a brand-color tile (League of Legends,
 *   Valorant, Fortnite, PlayStation).
 * - Wikimedia Commons public-domain originals, stored locally: EA Sports FC
 *   badge, Nintendo eShop bag mark (cropped from the 2025 eShop logo).
 * - EA SPORTS FC 25 Steam store capsule (official) as the EA FC cover.
 */
export interface GameAsset {
  logo: string;
  cover?: string;
}

const GAME_ASSETS: Record<string, GameAsset> = {
  "league-of-legends": { logo: "/gaming/logos/league-of-legends.svg" },
  valorant: { logo: "/gaming/logos/valorant.svg" },
  "pubg-mobile": { logo: "/gaming/logos/pubg-mobile.png", cover: "/gaming/covers/pubg-mobile.jpg" },
  "mobile-legends": { logo: "/gaming/logos/mobile-legends.png", cover: "/gaming/covers/mobile-legends.jpg" },
  roblox: { logo: "/gaming/logos/roblox.png" },
  fortnite: { logo: "/gaming/logos/fortnite.svg" },
  steam: { logo: "/gaming/logos/steam.png" },
  playstation: { logo: "/gaming/logos/playstation.svg" },
  xbox: { logo: "/gaming/logos/xbox.png" },
  nintendo: { logo: "/gaming/logos/nintendo.svg" },
  "ea-fc": { logo: "/gaming/logos/ea-fc.svg", cover: "/gaming/covers/ea-fc.jpg" },
  "genshin-impact": { logo: "/gaming/logos/genshin-impact.png", cover: "/gaming/covers/genshin-impact.jpg" },
  "cod-mobile": { logo: "/gaming/logos/cod-mobile.png", cover: "/gaming/covers/cod-mobile.jpg" },
  "clash-of-clans": { logo: "/gaming/logos/clash-of-clans.png", cover: "/gaming/covers/clash-of-clans.jpg" },
  "clash-royale": { logo: "/gaming/logos/clash-royale.png" },
  "brawl-stars": { logo: "/gaming/logos/brawl-stars.png", cover: "/gaming/covers/brawl-stars.jpg" },
  minecraft: { logo: "/gaming/logos/minecraft.png", cover: "/gaming/covers/minecraft.jpg" },
};

/** Artwork for a catalog slug, or `null` when none is bundled (callers show a neutral placeholder). */
export function gameAsset(slug: string | null | undefined): GameAsset | null {
  if (!slug) return null;
  return GAME_ASSETS[slug] ?? null;
}

/** Whether a verified cover is bundled for this slug (lets layouts reserve space only when useful). */
export function hasGameCover(slug: string): boolean {
  return Boolean(gameAsset(slug)?.cover);
}

/** Every mapped slug — exposed for tests that check coverage against the catalog. */
export const GAME_ASSET_SLUGS = Object.keys(GAME_ASSETS);
