import type { ComponentType } from "react";
import * as BrandIcons from "@icons-pack/react-simple-icons";
import { Layers3 } from "lucide-react";

type BrandIcon = ComponentType<{ size?: number; color?: string; title?: string }>;

const iconLibrary = BrandIcons as unknown as Record<string, BrandIcon>;

const providers: Record<string, { icon: string; color: string; surface: string }> = {
  netflix: { icon: "SiNetflix", color: "#E50914", surface: "rgba(229,9,20,.14)" },
  spotify: { icon: "SiSpotify", color: "#1ED760", surface: "rgba(30,215,96,.14)" },
  youtube: { icon: "SiYoutube", color: "#FF0033", surface: "rgba(255,0,51,.14)" },
  google: { icon: "SiGoogle", color: "#4285F4", surface: "rgba(66,133,244,.14)" },
  amazon: { icon: "SiAmazon", color: "#FF9900", surface: "rgba(255,153,0,.14)" },
  chatgpt: { icon: "SiOpenai", color: "#10A37F", surface: "rgba(16,163,127,.14)" },
  adobe: { icon: "SiAdobe", color: "#FF0000", surface: "rgba(255,0,0,.14)" },
};

function resolveProvider(name: string) {
  const key = name.toLocaleLowerCase("tr-TR");
  return Object.entries(providers).find(([provider]) => key.includes(provider))?.[1];
}

export function ProviderMark({ name, size = "md" }: { name: string; size?: "sm" | "md" | "lg" }) {
  const provider = resolveProvider(name);
  const dimension = size === "lg" ? 58 : size === "sm" ? 36 : 44;
  const iconSize = size === "lg" ? 28 : size === "sm" ? 17 : 21;
  const Icon = provider ? iconLibrary[provider.icon] : null;

  return (
    <span
      className="grid shrink-0 place-items-center rounded-[1rem] border border-white/10 shadow-lg shadow-slate-950/10"
      style={{ width: dimension, height: dimension, background: provider?.surface ?? "rgba(148,163,184,.12)", color: provider?.color ?? "#cbd5e1" }}
      data-testid={`provider-mark-${name.toLocaleLowerCase("tr-TR").replaceAll(" ", "-")}`}
      aria-label={`${name} amblemi`}
    >
      {Icon ? <Icon size={iconSize} color={provider?.color} title={name} /> : <Layers3 size={iconSize} />}
    </span>
  );
}
