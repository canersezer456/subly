import { describe, expect, it } from "vitest";
import { ApiError } from "@/lib/api";
import { apiErrorMessage, decodeStatementBytes, duplicateConflict, statementFileProblem } from "@/lib/subscriptionUi";

describe("apiErrorMessage", () => {
  it("shows structured mailbox errors instead of hiding their actionable message", () => {
    // 409 scope_missing
    expect(apiErrorMessage(new ApiError(409, { detail: { code: "scope_missing", message: "E-posta üstbilgilerini okuma izni eksik; hesabı yeniden bağla ve gerekli izni ver" } }))).toBe("E-posta üstbilgilerini okuma izni eksik; hesabı yeniden bağla ve gerekli izni ver");
    // 409 reauth_required
    expect(apiErrorMessage(new ApiError(409, { detail: { code: "reauth_required", message: "E-posta izni geçersiz; hesabı yeniden bağla" } }))).toBe("E-posta izni geçersiz; hesabı yeniden bağla");
    // 429 provider_quota (fatal rate limit)
    expect(apiErrorMessage(new ApiError(429, { detail: { code: "provider_quota", message: "E-posta sağlayıcısının kullanım sınırına ulaşıldı. Daha sonra tekrar dene; hesabı yeniden bağlamak gerekmez." } }))).toBe("E-posta sağlayıcısının kullanım sınırına ulaşıldı. Daha sonra tekrar dene; hesabı yeniden bağlamak gerekmez.");
    // 502 provider_unavailable
    expect(apiErrorMessage(new ApiError(502, { detail: "Sağlayıcıya ulaşılamıyor" }))).toBe("Sağlayıcıya ulaşılamıyor");
  });

  it("does not stringify unexpected error payloads", () => {
    for (const detail of [null, [], { message: 42 }, { token: "private-test-value" }]) {
      expect(apiErrorMessage(new ApiError(403, { detail }))).toBeNull();
    }
    expect(apiErrorMessage(new Error("private-test-value"))).toBeNull();
  });

  it("distinguishes successful/partial responses from fatal error responses", () => {
    // A 200 OK sync response is not an ApiError
    const fullSuccess = { scanned: 468, matched: 1, created: 1, merged: 0, skipped_rejected: 0, already_accepted: 0, partial: false, skipped: 0, candidates: [{ id: "c1", provider_name: "Netflix" }] };
    const partialSuccess = { scanned: 468, matched: 1, created: 1, merged: 0, skipped_rejected: 0, already_accepted: 0, partial: true, skipped: 32, candidates: [{ id: "c1", provider_name: "Netflix" }] };

    expect(apiErrorMessage(fullSuccess)).toBeNull();
    expect(apiErrorMessage(partialSuccess)).toBeNull();
    expect(partialSuccess.candidates.length).toBe(1);
    expect(partialSuccess.partial).toBe(true);
    expect(partialSuccess.skipped).toBe(32);
  });
});

describe("decodeStatementBytes", () => {
  it("keeps UTF-8 Turkish headers intact and drops the BOM", () => {
    const bytes = new TextEncoder().encode("﻿İşlem Tarihi;Açıklama;Borç\n");
    expect(decodeStatementBytes(bytes)).toBe("İşlem Tarihi;Açıklama;Borç\n");
  });

  it("decodes Windows-1254 bank exports without mojibake", () => {
    // "Açıklama;Borç" in Windows-1254: ç=0xE7, ı=0xFD
    const cp1254 = new Uint8Array([0x41, 0xe7, 0xfd, 0x6b, 0x6c, 0x61, 0x6d, 0x61, 0x3b, 0x42, 0x6f, 0x72, 0xe7]);
    const text = decodeStatementBytes(cp1254);
    expect(text).toBe("Açıklama;Borç");
    expect(text).not.toMatch(/Ã|�/);
  });
});

describe("statementFileProblem", () => {
  it("accepts small csv/txt exports only", () => {
    expect(statementFileProblem({ name: "ekstre.CSV", size: 1_000 })).toBeNull();
    expect(statementFileProblem({ name: "ekstre.txt", size: 1_000 })).toBeNull();
    expect(statementFileProblem({ name: "ekstre.xlsx", size: 1_000 })).toBe("type");
    expect(statementFileProblem({ name: "ekstre.csv", size: 600_000 })).toBe("size");
  });
});

describe("duplicateConflict", () => {
  it("extracts the structured 409 body and ignores other errors", () => {
    const body = { detail: { code: "possible_duplicate", message: "m", matches: [{ id: "1", name: "Netflix", price: 1, currency: "TRY", status: "active" }] } };
    expect(duplicateConflict(new ApiError(409, body))?.matches[0].name).toBe("Netflix");
    expect(duplicateConflict(new ApiError(409, { detail: "Bu aday zaten işlendi" }))).toBeNull();
    expect(duplicateConflict(new ApiError(422, body))).toBeNull();
    expect(duplicateConflict(new Error("x"))).toBeNull();
  });
});
