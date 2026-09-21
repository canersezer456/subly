# Subly Finance Restoration Plan

## Objective

Restore the uploaded `subly-finans-main.zip` as the existing Subly finance application and make the full app runnable for continued development.

## Preserved decisions

- Treat the uploaded ZIP as the source of truth for the current application.
- Preserve the existing UI, visual language, navigation, and user flows.
- Preserve the existing frontend, backend, database structure, authentication, and current functionality.
- Do not rebuild, redesign, simplify, or replace the application.
- Do not remove existing features or change behavior unless required to make the restored project run.
- Keep the work scoped to restoration and run-readiness rather than adding new product features.

## Restoration outcome

- The uploaded project is restored into the working application.
- Existing configuration is retained, with protected environment settings left unchanged.
- The frontend and backend start successfully using the project’s existing setup.
- Existing routes, authentication, API flows, persistence, and major screens remain available.
- Any restoration-only compatibility fixes are kept minimal and limited to issues that prevent the existing app from running.

## Assumptions to challenge

- No new features, integrations, visual redesign, or database migration is requested in this phase.
- Existing authentication and database behavior should be preserved rather than replaced with temporary substitutes.
- If the archive contains incomplete or conflicting setup instructions, the existing source code and configuration take priority; only the smallest necessary run-readiness adjustment will be made.
- If a pre-existing feature depends on unavailable external credentials or services, the app will be restored without changing that feature, and the dependency will be identified rather than silently removed.

## Approval boundary

Approval means proceeding only with restoration and minimal run-readiness fixes. Any redesign, feature addition, data-model change, authentication change, or removal of an existing capability requires a separate decision.