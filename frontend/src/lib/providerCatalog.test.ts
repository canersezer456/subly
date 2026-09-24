import { describe, expect, it } from "vitest";
import { foldSearch, providerIdForName, rankProviders } from "@/lib/providerCatalog";
import type { Provider } from "@/lib/types";

function provider(id: string, name: string, aliases: string[] = [], category = "streaming"): Provider {
  return { id, family: id, name, category, subscription_category: "Eğlence", aliases, plans: [], manage_url: "https://example.com", merchant_patterns: [], email_domains: [], default_currency: null, pricing: { status: "not_tracked" }, note: null };
}

// Mirrors the relevant slice of backend/lib/provider_catalog.py.
const catalog = [
  provider("netflix", "Netflix"),
  provider("prime-video", "Prime Video", ["amazon prime video", "prime"]),
  provider("max", "Max", ["hbo max", "blutv"]),
  provider("chatgpt-plus", "ChatGPT Plus", ["chatgpt", "openai"], "ai"),
  provider("chatgpt-pro", "ChatGPT Pro", ["chatgpt", "openai"], "ai"),
  provider("claude-pro", "Claude Pro", ["claude"], "ai"),
  provider("claude-max", "Claude Max", ["claude"], "ai"),
  provider("amazon-prime", "Amazon Prime", ["prime", "amazon"], "bundle"),
];
const ids = (query: string) => rankProviders(catalog, query).map((p) => p.id);

describe("rankProviders", () => {
  it("returns every plan of a product for its brand name", () => {
    expect(ids("ChatGPT").slice(0, 2).sort()).toEqual(["chatgpt-plus", "chatgpt-pro"]);
    expect(ids("claude").slice(0, 2).sort()).toEqual(["claude-max", "claude-pro"]);
  });

  it("shows both Prime Video and Amazon Prime for 'Prime'", () => {
    expect(ids("Prime").sort()).toEqual(["amazon-prime", "prime-video"]);
  });

  it("ranks the exact service first for 'Max' (before Claude Max)", () => {
    expect(ids("max")[0]).toBe("max");
    expect(ids("max")).toContain("claude-max");
  });

  it("finds rebranded services by their former name", () => {
    expect(ids("BluTV")).toEqual(["max"]);
  });

  it("returns the whole catalog for an empty query and nothing for gibberish", () => {
    expect(ids("")).toHaveLength(catalog.length);
    expect(ids("zzzz")).toEqual([]);
  });
});

describe("providerIdForName", () => {
  it("maps exact legacy names only — no fuzzy guessing", () => {
    expect(providerIdForName("Netflix")).toBe("netflix");
    expect(providerIdForName("  YouTube   Premium ")).toBe("youtube-premium");
    expect(providerIdForName("Google One")).toBe("google-one");
    expect(providerIdForName("Netflix Aile Paylaşımı")).toBeNull();
  });
});

describe("foldSearch", () => {
  it("is case- and diacritic-insensitive, including Turkish dotless i", () => {
    expect(foldSearch("  Exxen   SPOR ")).toBe("exxen spor");
    expect(foldSearch("Müzik İÇİN ılık")).toBe("muzik icin ilik");
  });
});
