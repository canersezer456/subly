import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

export type FieldValue = string | number | boolean;
export type FormValues = Record<string, FieldValue>;

export interface FieldDef {
  name: string;
  label: string;
  type?: "text" | "number" | "date" | "month" | "url" | "select" | "checkbox" | "textarea";
  options?: { value: string; label: string }[];
  required?: boolean;
  placeholder?: string;
  full?: boolean;
  hint?: string;
}

export const opts = (values: string[]) => values.map((value) => ({ value, label: value }));
export const labelled = (map: Record<string, string>) => Object.entries(map).map(([value, label]) => ({ value, label }));

const controlClass = "h-10 w-full rounded-lg border border-input bg-background px-3 text-sm text-foreground shadow-none outline-none transition-[border-color,box-shadow] focus-visible:border-primary focus-visible:ring-2 focus-visible:ring-primary/25";

/** Schema-driven create/edit dialog shared by every finance record type. */
export function EntityDialog({ open, title, description, fields, initial, onClose, onSubmit, busy, submitLabel, testId }: {
  open: boolean; title: string; description?: string; fields: FieldDef[]; initial: FormValues; onClose: () => void;
  onSubmit: (values: FormValues) => void; busy?: boolean; submitLabel?: string; testId: string;
}) {
  const [values, setValues] = useState<FormValues>(initial);
  useEffect(() => { if (open) setValues(initial); }, [open, initial]);
  const set = (name: string, value: FieldValue) => setValues((old) => ({ ...old, [name]: value }));

  const submit = (event: FormEvent) => {
    event.preventDefault();
    onSubmit(values);
  };

  return (
    <Dialog open={open} onOpenChange={(next) => !next && onClose()}>
      <DialogContent className="max-h-[92svh] overflow-y-auto border-border bg-card sm:max-w-lg" data-testid={testId}>
        <DialogHeader>
          <DialogTitle className="font-heading text-lg" data-testid={`${testId}-title`}>{title}</DialogTitle>
          {description && <DialogDescription data-testid={`${testId}-description`}>{description}</DialogDescription>}
        </DialogHeader>
        <form onSubmit={submit} className="mt-2 grid gap-4 sm:grid-cols-2" data-testid={`${testId}-form`}>
          {fields.map((field) => {
            const id = `${testId}-field-${field.name}`;
            const value = values[field.name];
            const wrap = cn("space-y-1.5", (field.full || field.type === "textarea") && "sm:col-span-2");
            if (field.type === "checkbox") {
              return (
                <label key={field.name} className={cn(wrap, "flex items-center gap-3 rounded-lg border border-border px-3 py-2.5 text-sm")}>
                  <input id={id} type="checkbox" checked={Boolean(value)} onChange={(e) => set(field.name, e.target.checked)} className="h-4 w-4 accent-[var(--primary)]" data-testid={id} />
                  <span>{field.label}</span>
                </label>
              );
            }
            return (
              <div key={field.name} className={wrap}>
                <label htmlFor={id} className="text-xs text-muted-foreground">{field.label}</label>
                {field.type === "select" ? (
                  <select id={id} value={String(value ?? "")} onChange={(e) => set(field.name, e.target.value)} className={controlClass} required={field.required} data-testid={id}>
                    {field.options?.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
                  </select>
                ) : field.type === "textarea" ? (
                  <textarea id={id} value={String(value ?? "")} onChange={(e) => set(field.name, e.target.value)} placeholder={field.placeholder} rows={2} className={cn(controlClass, "h-auto py-2")} data-testid={id} />
                ) : (
                  <Input id={id} type={field.type ?? "text"} value={field.type === "number" ? (value === 0 || value === "" ? "" : String(value)) : String(value ?? "")} min={field.type === "number" ? "0" : undefined} step={field.type === "number" ? "0.01" : undefined}
                    onChange={(e) => set(field.name, field.type === "number" ? Number(e.target.value) : e.target.value)} placeholder={field.placeholder} required={field.required} className={controlClass} data-testid={id} />
                )}
                {field.hint && <p className="text-[11px] text-muted-foreground/80">{field.hint}</p>}
              </div>
            );
          })}
          <div className="mt-1 flex justify-end gap-2 sm:col-span-2">
            <Button type="button" variant="ghost" onClick={onClose} data-testid={`${testId}-cancel`}>Vazgeç</Button>
            <Button type="submit" disabled={busy} className="bg-primary text-primary-foreground hover:bg-primary/90" data-testid={`${testId}-submit`}>{busy ? "Kaydediliyor…" : submitLabel ?? "Kaydet"}</Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
