import { useState } from "react";
import { cn } from "@/lib/utils";

/**
 * Game icon with a safe fallback — never a broken browser image glyph.
 *
 * The backend's game catalog (backend/lib/gaming_catalog.py) hotlinks game
 * logos directly from upload.wikimedia.org thumbnail URLs. Verified (curl,
 * every one) that all of them now 400 — the underlying Commons files were
 * renamed/moved since the catalog was authored; git history shows this was
 * never any different (baked in from the first commit). Hotlinking a third
 * party's exact thumbnail path is inherently fragile and out of our control,
 * so this component does not depend on it rendering successfully.
 *
 * Render order: a colored initial-letter badge (using the game's own
 * `accentColor`, mirroring the sidebar's user-avatar-initial fallback and
 * ProviderMark's colored-surface pattern) is always in the DOM first. The
 * <img> — if a url is given — loads on top of it, invisible (opacity-0)
 * until `onLoad` confirms success, then fades in and covers the letter. On
 * `onError` the <img> unmounts entirely. Because the image is never visible
 * before a confirmed successful load, no failed/broken image state can ever
 * flash on screen — this holds regardless of whether `iconUrl` ever starts
 * resolving again.
 */
export function GameMark({ name, iconUrl, accentColor, size = 44, rounded = "xl", testId }: {
  name: string;
  iconUrl?: string | null;
  accentColor: string;
  size?: number;
  rounded?: "lg" | "xl" | "2xl";
  testId?: string;
}) {
  const [loaded, setLoaded] = useState(false);
  const [failed, setFailed] = useState(false);
  const showImage = loaded && !failed;
  const roundedClass = rounded === "lg" ? "rounded-lg" : rounded === "2xl" ? "rounded-2xl" : "rounded-xl";

  return (
    <span
      className={cn("relative grid shrink-0 place-items-center overflow-hidden", roundedClass)}
      style={{ width: size, height: size, backgroundColor: `${accentColor}22`, color: accentColor }}
      data-testid={testId}
      aria-label={name}
    >
      <span className="font-heading font-bold" style={{ fontSize: Math.round(size * 0.42) }} aria-hidden="true">
        {name.slice(0, 1).toUpperCase()}
      </span>
      {iconUrl && !failed && (
        <img
          src={iconUrl}
          alt=""
          aria-hidden="true"
          loading="lazy"
          onLoad={() => setLoaded(true)}
          onError={() => setFailed(true)}
          className={cn("absolute inset-0 h-full w-full object-contain p-1.5 transition-opacity duration-150", showImage ? "opacity-100" : "opacity-0")}
        />
      )}
    </span>
  );
}
