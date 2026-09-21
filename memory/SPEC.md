# Subly — Kişisel Finans İşletim Sistemi (MVP Spec)

## Product
Subly is a Turkish personal / household economy assistant. After email+password or Emergent Google login, users manage income, expenses, subscriptions, bills, a payment calendar, monthly budgets, a savings engine, smart alerts and a data-grounded AI assistant from one sidebar-driven dashboard. Dark theme default; light theme toggle in the topbar / Settings.

## Data model (Mongo, per-user via `user_id`)
- `users`, `user_sessions` — unchanged (PBKDF2 password hash, httpOnly Secure cookie session)
- `incomes`: source, amount, kind (regular | one_time | extra), date, note
- `expenses`: title, amount, category, date, payment_method, note
- `bills`: provider, bill_type, amount, due_date, frequency (monthly | bimonthly | quarterly | yearly | once), auto_pay, payment_method, bill_number, note, status (pending | paid)
- `budgets`: category, limit, month ("" = every month)
- `subscriptions`: + `billing_cycle` (monthly | yearly), `usage` (active | rarely | unused)
- `assistant_messages`: role, content, created_at
- `digest_prefs`: enabled, weekday, hour, origin, last_sent_at, reminders_enabled, reminder_hour, last_reminder_date (one per user)

## Computation rules (backend/lib/finance.py, "today" = Europe/Istanbul)
- Month income = regular incomes (every month from their start date) + one-off/extra incomes dated in the month.
- Month expense = manual expenses in month + bills due in month (recurring ones projected) + active subscriptions' monthly cost (yearly/12; USD/EUR converted with approximate static rates). Bills/subscriptions appear as "Faturalar"/"Abonelikler" categories.
- Upcoming = pending/recurring bills + subscription renewals in the next 30 days.
- Budget usage compares category breakdown to limits; exceeded / >=85% flags.
- Savings insights: unused subs (red), rarely used subs (yellow, 50%), exceeded budgets (yellow), bill >20% above previous same-provider bill (yellow), yearly-plan alternative for monthly subs >= ₺50 (green, 16%).
- Alerts: due within 3 days, budget exceeded / >=85%, unused subs, month-over-month spend +10%, potential savings.

## API (all under /api, session required unless noted)
- auth: register / login / me / logout / google/session (public)
- CRUD (`lib/crud.py` factory): /incomes, /expenses, /bills, /budgets — GET (?month=YYYY-MM), POST (201), PATCH /{id}, DELETE /{id}
- /subscriptions (+ /mock-scan, /deals) — existing
- /dashboard/summary, /calendar?month=, /savings, /alerts
- /assistant/history (GET, DELETE), POST /assistant/chat → SSE stream (`data: {"delta"}` … `{"done": true}`), GPT-5.4 via emergentintegrations + EMERGENT_LLM_KEY
- /account/export (GET JSON dump), DELETE /account (erase everything + session)
- /digest/preferences (GET, PUT {enabled, weekday 0=Mon, hour}), /digest/preview (GET subject+html), POST /digest/send-now (to the user's own stored email; 10-min rate limit) — Emergent-managed Resend proxy via `lib/email.py` (guardrail gate on every send, `from_name` = EMAIL_FROM_NAME=Subly). `lib/digest.py` builds the fixed template (month summary, next-7-day payments, top 3 savings tips, app links from the saved origin) and runs an in-process scheduler every 10 min that sends to opted-in users at their weekday/hour (Europe/Istanbul), max once per 6 days.
- Same-day payment reminder: `digest_prefs.reminders_enabled` + `reminder_hour` (default 08:00 Istanbul). Scheduler sends one email per day (`last_reminder_date`) listing bills/subscription renewals due today (paid bills excluded); nothing due → nothing sent. Endpoints: GET /digest/reminder-preview, POST /digest/send-reminder-now (409 if nothing due, 429 if already sent today).

## Frontend
- `/` login (Home.tsx). Protected routes under `AppShell` (sidebar + topbar alerts + mobile bottom nav): /dashboard, /expenses, /incomes, /subscriptions (?tab=list|scan|deals), /bills, /calendar, /budget, /savings, /assistant, /household (roadmap placeholder), /settings (theme, weekly digest email toggle/day/hour + preview iframe + "Şimdi gönder", privacy explainer, export, delete account).
- Shared: `hooks/useCrud.ts`, `components/shared/EntityDialog.tsx` (schema-driven form; field testids `${dialog}-field-${name}`), `components/shared/ui-bits.tsx`.
- TS interfaces in `lib/types.ts` mirror Pydantic models 1:1.

## Seeding
- Every new account gets 4 starter subscriptions. Only `demo@subly.app` also gets sample incomes/expenses/bills/budgets (`lib/seed.py`), dated relative to today so upcoming payments always show.

## Known boundaries (MOCKED / not yet built)
Bank/card scan and deal prices are simulated/example data. Gmail/Outlook discovery, bank connections, OCR, 2FA and household sharing are surfaced as "Yakında" and not functional. FX rates for USD/EUR subscriptions are static approximations. The demo account's address (demo@subly.app) is not a real mailbox, so "Şimdi gönder" returns a clear 422 there; real accounts receive the email.
