import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { GAME_ASSET_SLUGS, gameAsset, hasGameCover } from "@/lib/gameAssets";

const frontendRoot = path.resolve(__dirname, "../..");
const publicDir = path.join(frontendRoot, "public");
const catalogPath = path.resolve(frontendRoot, "../backend/lib/gaming_catalog.py");

function catalogSlugs(): string[] {
  const source = readFileSync(catalogPath, "utf-8");
  return [...source.matchAll(/"slug":\s*"([^"]+)"/g)].map((m) => m[1]);
}

function assetPaths(): string[] {
  return GAME_ASSET_SLUGS.flatMap((slug) => {
    const asset = gameAsset(slug)!;
    return asset.cover ? [asset.logo, asset.cover] : [asset.logo];
  });
}

describe("gameAssets", () => {
  it("maps a logo for every game in the backend catalog", () => {
    const slugs = catalogSlugs();
    expect(slugs.length).toBeGreaterThan(0);
    const missing = slugs.filter((slug) => !gameAsset(slug)?.logo);
    expect(missing).toEqual([]);
  });

  it("has no stale entries for slugs the catalog no longer contains", () => {
    const slugs = new Set(catalogSlugs());
    expect(GAME_ASSET_SLUGS.filter((slug) => !slugs.has(slug))).toEqual([]);
  });

  it("only references bundled files, never a remote (e.g. Wikimedia) URL", () => {
    for (const p of assetPaths()) {
      expect(p).toMatch(/^\/gaming\/(logos|covers)\/[a-z0-9-]+\.(png|jpg|svg)$/);
    }
  });

  it("every referenced file exists and its content matches its extension", () => {
    for (const p of assetPaths()) {
      const file = path.join(publicDir, p);
      expect(existsSync(file), p).toBe(true);
      const head = readFileSync(file).subarray(0, 8);
      if (p.endsWith(".png")) expect(head.subarray(0, 4).toString("hex"), p).toBe("89504e47");
      else if (p.endsWith(".jpg")) expect(head.subarray(0, 3).toString("hex"), p).toBe("ffd8ff");
      else expect(readFileSync(file, "utf-8").trimStart().startsWith("<svg"), p).toBe(true);
    }
  });

  it("returns null for unknown or empty slugs so callers fall back to a placeholder", () => {
    expect(gameAsset("not-a-game")).toBeNull();
    expect(gameAsset("")).toBeNull();
    expect(gameAsset(undefined)).toBeNull();
    expect(hasGameCover("not-a-game")).toBe(false);
  });

  it("keeps logo and cover distinct wherever a cover exists", () => {
    for (const slug of GAME_ASSET_SLUGS) {
      const asset = gameAsset(slug)!;
      if (asset.cover) expect(asset.cover).not.toBe(asset.logo);
    }
  });
});
