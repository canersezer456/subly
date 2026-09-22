import { describe, expect, it } from "vitest";
import { RATES, fromTry, toTry } from "@/lib/currency";

describe("toTry", () => {
  it("returns TRY amounts unchanged", () => {
    expect(toTry(100, "TRY")).toBe(100);
  });

  it("converts USD to TRY using the shared RATES table", () => {
    expect(toTry(10, "USD")).toBe(10 * RATES.USD);
  });

  it("converts EUR to TRY using the shared RATES table", () => {
    expect(toTry(10, "EUR")).toBe(10 * RATES.EUR);
  });

  it("treats an unknown currency code as a 1:1 rate rather than throwing", () => {
    expect(toTry(50, "XXX")).toBe(50);
  });
});

describe("fromTry", () => {
  it("returns TRY amounts unchanged", () => {
    expect(fromTry(1000, "TRY")).toBe(1000);
  });

  it("is the inverse of toTry for USD", () => {
    const originalUsd = 25;
    const asTry = toTry(originalUsd, "USD");
    expect(fromTry(asTry, "USD")).toBeCloseTo(originalUsd, 10);
  });

  it("is the inverse of toTry for EUR", () => {
    const originalEur = 40;
    const asTry = toTry(originalEur, "EUR");
    expect(fromTry(asTry, "EUR")).toBeCloseTo(originalEur, 10);
  });
});
