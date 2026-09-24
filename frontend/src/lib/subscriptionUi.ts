/** Non-component helpers shared by the subscription hub UI. */
import { ApiError } from "@/lib/api";
import type { DuplicateConflict } from "@/lib/types";

export type Translate = (key: string, vars?: Record<string, string | number>) => string;

export function cycleLabel(t: Translate, cycle: string | null | undefined): string {
  if (cycle === "yearly") return t("subscriptions.cycle.yearly");
  if (cycle === "quarterly") return t("subsHub.cycle.quarterly");
  return t("subscriptions.cycle.monthly");
}

/** The structured 409 body create/accept return when a matching subscription may already exist. */
export function duplicateConflict(error: unknown): DuplicateConflict | null {
  if (!(error instanceof ApiError) || error.status !== 409) return null;
  const detail = (error.body as { detail?: unknown } | null)?.detail;
  if (detail && typeof detail === "object" && (detail as DuplicateConflict).code === "possible_duplicate") return detail as DuplicateConflict;
  return null;
}

export function apiErrorMessage(error: unknown): string | null {
  if (!(error instanceof ApiError)) return null;
  const detail = (error.body as { detail?: unknown } | null)?.detail;
  if (typeof detail === "string") return detail;
  if (detail && typeof detail === "object" && "message" in detail && typeof detail.message === "string") return detail.message;
  return null;
}

export const STATUS_OPTIONS = ["active", "paused", "cancelled", "expired"] as const;
export const CYCLE_OPTIONS = ["monthly", "quarterly", "yearly"] as const;
export const CURRENCY_OPTIONS = ["TRY", "USD", "EUR"] as const;

export const STATEMENT_FILE_MAX_BYTES = 500_000;

/** Why a picked statement file can't be used, or null. Only .csv/.txt text exports. */
export function statementFileProblem(file: { name: string; size: number }): "type" | "size" | null {
  if (!/\.(csv|txt)$/i.test(file.name)) return "type";
  if (file.size > STATEMENT_FILE_MAX_BYTES) return "size";
  return null;
}

/**
 * Decode a bank CSV export. Turkish banks often export Windows-1254 rather than UTF-8;
 * decoding those as UTF-8 would turn "Açıklama" into mojibake and break column detection.
 * Strict UTF-8 first, then Windows-1254. The file never leaves the browser except as the
 * decoded text sent to the import endpoint (not stored there).
 */
export function decodeStatementBytes(bytes: ArrayBuffer | Uint8Array): string {
  const view = bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes);
  try {
    return new TextDecoder("utf-8", { fatal: true }).decode(view).replace(/^﻿/, "");
  } catch {
    return new TextDecoder("windows-1254").decode(view);
  }
}
