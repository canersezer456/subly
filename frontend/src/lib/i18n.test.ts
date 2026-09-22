import { describe, expect, it } from "vitest";
import { interpolate, translate } from "@/lib/i18n";

describe("interpolate", () => {
  it("substitutes {placeholder} tokens from vars", () => {
    expect(interpolate("Merhaba {name}", { name: "Ada" })).toBe("Merhaba Ada");
  });

  it("leaves unmatched placeholders untouched instead of throwing", () => {
    expect(interpolate("Merhaba {name}", {})).toBe("Merhaba {name}");
  });

  it("returns the template unchanged when no vars are given", () => {
    expect(interpolate("Sabit metin")).toBe("Sabit metin");
  });

  it("substitutes numeric values too", () => {
    expect(interpolate("{count} kayıt", { count: 3 })).toBe("3 kayıt");
  });
});

describe("translate (i18n fallback chain)", () => {
  const active = { "a.key": "Aktif dil değeri" };
  const english = { "a.key": "English fallback", "b.key": "English only" };

  it("prefers the active language's value when present", () => {
    expect(translate(active, english, "a.key")).toBe("Aktif dil değeri");
  });

  it("falls back to English when the key is missing in the active dict", () => {
    expect(translate(active, english, "b.key")).toBe("English only");
  });

  it("falls back to the raw key when missing everywhere, and never throws", () => {
    expect(translate(active, english, "totally.missing.key")).toBe("totally.missing.key");
  });

  it("interpolates through the fallback chain", () => {
    expect(translate({}, { "c.key": "Hello {name}" }, "c.key", { name: "World" })).toBe("Hello World");
  });
});
