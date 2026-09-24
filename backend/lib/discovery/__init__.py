"""Subscription discovery.

Discovery never writes to `subscriptions`. Every source (e-mail, card/bank
transactions, user-supplied import) turns its signals into *candidates*
(`subscription_candidates` collection) that the owning user explicitly accepts
or rejects. See lib/discovery/candidates.py.

Source status (kept honest, surfaced by GET /subscriptions/discovery/status):
- email:       Gmail/Outlook adapters exist but no OAuth client is configured, so
               no mailbox is ever read. `classify_email` is the pure analysis step
               a connected adapter will feed.
- transaction: no bank/card aggregator is configured; no transactions are fetched
               or fabricated. Merchant normalization + recurrence detection are
               implemented and exercised by the import source.
- import:      works today — the user pastes their own statement lines.
"""
