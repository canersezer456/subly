import { useState } from "react";
import { Gamepad2 } from "lucide-react";
import { gameAsset } from "@/lib/gameAssets";
import { cn } from "@/lib/utils";

/**
 * Game logo tile, resolved from the bundled asset map (`@/lib/gameAssets`)
 * by catalog slug — never from the backend's dead Wikimedia `icon_url`.
 *
 * A neutral gamepad placeholder is always in the DOM first. The <img> loads
 * on top of it, invisible (opacity-0) until `onLoad` confirms success; on
 * `onError` it unmounts. So neither a broken-image glyph nor a guessed letter
 * can ever show: a game without a verified logo simply keeps the placeholder.
 */
export function GameMark({ slug, alt, size = 44, rounded = "xl", testId }: {
  slug: string;
  /** Accessible name, e.g. "Valorant logosu". */
  alt: string;
  size?: number;
  rounded?: "lg" | "xl" | "2xl";
  testId?: string;
}) {
  const logo = gameAsset(slug)?.logo;
  const [loaded, setLoaded] = useState(false);
  const [failed, setFailed] = useState(false);
  const showImage = loaded && !failed;
  const roundedClass = rounded === "lg" ? "rounded-lg" : rounded === "2xl" ? "rounded-2xl" : "rounded-xl";

  return (
    <span
      className={cn("relative grid shrink-0 place-items-center overflow-hidden bg-muted text-muted-foreground", roundedClass)}
      style={{ width: size, height: size }}
      data-testid={testId}
      data-asset={showImage ? "logo" : "placeholder"}
      role="img"
      aria-label={alt}
    >
      <Gamepad2 size={Math.round(size * 0.5)} aria-hidden="true" className={cn("transition-opacity", showImage && "opacity-0")} />
      {logo && !failed && (
        <img
          src={logo}
          alt=""
          aria-hidden="true"
          width={size}
          height={size}
          decoding="async"
          loading="lazy"
          draggable={false}
          onLoad={() => setLoaded(true)}
          onError={() => setFailed(true)}
          className={cn("absolute inset-0 h-full w-full object-cover transition-opacity duration-150", showImage ? "opacity-100" : "opacity-0")}
        />
      )}
    </span>
  );
}

/**
 * Landscape game artwork (hero / deal cards). Renders nothing until the image
 * has loaded, and nothing at all when the game has no verified cover or the
 * file fails — the caller's own background shows through instead.
 */
export function GameCover({ slug, alt, className, testId }: {
  slug: string;
  /** Accessible description, e.g. "PUBG Mobile kapak görseli". */
  alt: string;
  className?: string;
  testId?: string;
}) {
  const cover = gameAsset(slug)?.cover;
  const [loaded, setLoaded] = useState(false);
  const [failed, setFailed] = useState(false);
  if (!cover || failed) return null;
  return (
    <img
      src={cover}
      alt={alt}
      decoding="async"
      loading="lazy"
      draggable={false}
      onLoad={() => setLoaded(true)}
      onError={() => setFailed(true)}
      data-testid={testId}
      className={cn("h-full w-full object-cover transition-opacity duration-200", loaded ? "opacity-100" : "opacity-0", className)}
    />
  );
}
