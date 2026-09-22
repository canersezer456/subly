import { describe, expect, it } from "vitest";
import { categoryLabel, billTypeLabel, frequencyLabel, subscriptionCategoryLabel, paymentMethodLabel, usageLabel, incomeKindLabel } from "@/lib/format";

// A fake t() that just prefixes the key — enough to prove the *Label()
// helpers look up the right key and never touch the stored value itself.
const fakeT = (key: string) => `T(${key})`;

describe("categoryLabel (stored value never changes, only the display label)", () => {
  it("translates a known stored category to its i18n key", () => {
    expect(categoryLabel(fakeT, "Market")).toBe("T(category.market)");
  });

  it("falls back to the raw stored value for an unmapped/custom category", () => {
    expect(categoryLabel(fakeT, "Bir Gün Uydurduğum Kategori")).toBe("Bir Gün Uydurduğum Kategori");
  });
});

describe("billTypeLabel", () => {
  it("translates a known bill type", () => {
    expect(billTypeLabel(fakeT, "Elektrik")).toBe("T(billType.electricity)");
  });

  it("falls back to the raw value when unmapped", () => {
    expect(billTypeLabel(fakeT, "Bilinmeyen Tür")).toBe("Bilinmeyen Tür");
  });
});

describe("subscriptionCategoryLabel", () => {
  it("translates a known subscription category", () => {
    expect(subscriptionCategoryLabel(fakeT, "Müzik")).toBe("T(subCategory.music)");
  });
});

describe("paymentMethodLabel", () => {
  it("translates a known payment method, including masked-card entries", () => {
    expect(paymentMethodLabel(fakeT, "Nakit")).toBe("T(paymentMethod.cash)");
    expect(paymentMethodLabel(fakeT, "Kart •••• 4821")).toBe("T(paymentMethod.card1)");
  });
});

describe("code-keyed enum labels (frequency/usage/income kind)", () => {
  it("translates a known frequency code", () => {
    expect(frequencyLabel(fakeT, "monthly")).toBe("T(enum.frequency.monthly)");
  });

  it("falls back to the raw code for an unknown frequency", () => {
    expect(frequencyLabel(fakeT, "weekly")).toBe("weekly");
  });

  it("translates a known usage code", () => {
    expect(usageLabel(fakeT, "unused")).toBe("T(enum.usage.unused)");
  });

  it("translates a known income kind code", () => {
    expect(incomeKindLabel(fakeT, "one_time")).toBe("T(enum.incomeKind.oneTime)");
  });
});
