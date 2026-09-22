import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Bot, Eraser, SendHorizonal, ShieldCheck, Sparkles } from "lucide-react";
import { ApiError, apiDelete, apiGet, apiStream } from "@/lib/api";
import { useT } from "@/lib/i18n";
import type { AssistantMessage } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { PageHeader } from "@/components/shared/ui-bits";

// Phase 4: distinct copy per SSE error `code` (routers/assistant.py) instead of one
// generic message — budget_exceeded/circuit_open are not worth retrying immediately,
// unlike a one-off provider hiccup. Missing/unknown codes fall back to the original
// generic message, unchanged from before Phase 4.

export default function Assistant() {
  const { t } = useT();
  const ASSISTANT_ERROR_MESSAGES: Record<string, string> = {
    budget_exceeded: t("assistant.error.budgetExceeded"),
    circuit_open: t("assistant.error.circuitOpen"),
  };
  const DEFAULT_ASSISTANT_ERROR_MESSAGE = t("assistant.error.default");
  const SUGGESTIONS = [
    t("assistant.suggestion.spend"),
    t("assistant.suggestion.upcoming"),
    t("assistant.suggestion.unused"),
    t("assistant.suggestion.savings"),
    t("assistant.suggestion.compare"),
    t("assistant.suggestion.budget"),
  ];
  const queryClient = useQueryClient();
  const history = useQuery({ queryKey: ["assistant-history"], queryFn: () => apiGet<AssistantMessage[]>("/assistant/history"), retry: false });
  const [draft, setDraft] = useState("");
  const [pending, setPending] = useState<{ question: string; answer: string } | null>(null);
  const [streaming, setStreaming] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  const messages = history.data ?? [];
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages.length, pending?.answer]);

  const ask = async (question: string) => {
    const text = question.trim();
    if (!text || streaming) return;
    setDraft("");
    setStreaming(true);
    setPending({ question: text, answer: "" });
    try {
      await apiStream("/assistant/chat", { message: text }, (delta) => setPending((p) => (p ? { ...p, answer: p.answer + delta } : p)));
    } catch (error) {
      const code = error instanceof ApiError ? error.code : undefined;
      toast.error((code && ASSISTANT_ERROR_MESSAGES[code]) || DEFAULT_ASSISTANT_ERROR_MESSAGE);
    } finally {
      await queryClient.invalidateQueries({ queryKey: ["assistant-history"] });
      setPending(null);
      setStreaming(false);
    }
  };

  const clear = useMutation({ mutationFn: () => apiDelete<void>("/assistant/history"), onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["assistant-history"] }); toast.success(t("assistant.cleared")); } });
  const submit = (e: FormEvent) => { e.preventDefault(); void ask(draft); };
  const empty = messages.length === 0 && !pending;

  return (
    <div className="flex min-h-[calc(100svh-9rem)] flex-col" data-testid="assistant-page">
      <PageHeader eyebrow={t("assistant.eyebrow")} title={t("assistant.title")} description={t("assistant.description")} testId="assistant-header"
        actions={messages.length > 0 && <Button variant="ghost" size="sm" onClick={() => clear.mutate()} className="text-muted-foreground" data-testid="assistant-clear-button"><Eraser size={14} /> {t("assistant.clearChat")}</Button>} />

      <div className="flex flex-1 flex-col rounded-2xl border border-border bg-card" data-testid="assistant-chat">
        <div className="flex-1 space-y-4 overflow-y-auto p-4 sm:p-6" data-testid="assistant-messages">
          {empty && (
            <div className="mx-auto max-w-xl py-8 text-center" data-testid="assistant-empty">
              <span className="mx-auto mb-4 grid h-12 w-12 place-items-center rounded-2xl bg-primary/15 text-primary"><Bot size={22} /></span>
              <p className="font-heading text-lg font-semibold">{t("assistant.empty.title")}</p>
              <p className="mt-2 text-sm text-muted-foreground">{t("assistant.empty.description")}</p>
            </div>
          )}
          {messages.map((m) => <Bubble key={m.id} role={m.role} content={m.content} testId={`assistant-message-${m.id}`} />)}
          {pending && <>
            <Bubble role="user" content={pending.question} testId="assistant-message-pending-user" />
            <Bubble role="assistant" content={pending.answer || "…"} streaming testId="assistant-message-pending-assistant" />
          </>}
          <div ref={bottomRef} />
        </div>

        <div className="border-t border-border p-3 sm:p-4">
          <div className="mb-3 flex gap-2 overflow-x-auto pb-1" data-testid="assistant-suggestions">
            {SUGGESTIONS.map((s) => <button key={s} type="button" onClick={() => void ask(s)} disabled={streaming} className="shrink-0 rounded-full border border-border bg-background px-3 py-1.5 text-xs text-muted-foreground transition-colors hover:border-primary/50 hover:text-foreground disabled:opacity-50" data-testid="assistant-suggestion">{s}</button>)}
          </div>
          <form onSubmit={submit} className="flex gap-2" data-testid="assistant-form">
            <Input value={draft} onChange={(e) => setDraft(e.target.value)} placeholder={t("assistant.inputPlaceholder")} className="h-11 flex-1" disabled={streaming} data-testid="assistant-input" />
            <Button type="submit" disabled={streaming || !draft.trim()} className="h-11 bg-primary px-4 text-primary-foreground hover:bg-primary/90" data-testid="assistant-send-button"><SendHorizonal size={16} /></Button>
          </form>
          <p className="mt-2 flex items-center gap-1 text-[11px] text-muted-foreground" data-testid="assistant-privacy-note"><ShieldCheck size={12} className="text-primary" /> {t("assistant.privacyNote")}</p>
        </div>
      </div>
    </div>
  );
}

function Bubble({ role, content, streaming, testId }: { role: "user" | "assistant"; content: string; streaming?: boolean; testId: string }) {
  const isUser = role === "user";
  return (
    <div className={cn("flex gap-3", isUser && "justify-end")} data-testid={testId}>
      {!isUser && <span className="mt-1 grid h-8 w-8 shrink-0 place-items-center rounded-xl bg-primary/15 text-primary"><Sparkles size={14} /></span>}
      <div className={cn("max-w-[85%] whitespace-pre-wrap rounded-2xl px-4 py-3 text-sm leading-relaxed sm:max-w-[70%]", isUser ? "bg-primary text-primary-foreground" : "bg-muted text-foreground", streaming && "animate-pulse-soft")}>{isUser ? content : renderLite(content)}</div>
    </div>
  );
}

/** Minimal markdown: **bold**, "- " bullets, "### " headings. Enough for the assistant's short answers. */
function renderLite(text: string) {
  return text.split("\n").map((line, i) => {
    const heading = line.match(/^#{1,3}\s+(.*)$/);
    const bullet = line.match(/^\s*[-*]\s+(.*)$/);
    const body = heading?.[1] ?? bullet?.[1] ?? line;
    const parts = body.split(/(\*\*[^*]+\*\*)/g).map((part, j) => part.startsWith("**") && part.endsWith("**") ? <strong key={j} className="font-semibold">{part.slice(2, -2)}</strong> : part);
    if (heading) return <p key={i} className="mt-1 font-semibold">{parts}</p>;
    if (bullet) return <p key={i} className="flex gap-2 pl-1"><span className="text-primary">•</span><span>{parts}</span></p>;
    return <p key={i}>{parts}</p>;
  });
}
