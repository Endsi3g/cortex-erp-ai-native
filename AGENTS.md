# Instructions for AI agents working in Cortex

Before changing the product UI, read [`docs/frontend/CORTEX_UI_HANDOFF_V2.md`](docs/frontend/CORTEX_UI_HANDOFF_V2.md). It is the canonical frontend/product contract for every agent and supersedes older frontend descriptions in `HANDOFF.md`.

Keep ERPNext/Frappe as the system of record; build with native ERPNext/Frappe constructions first (workspaces, number cards, charts, reports, list/form/calendar scripts; Frappe's own bundler only for the AI home). Vite, Frappe UI and a separate SPA are retired; send all writes through permission-checked Frappe domain APIs. Do not invent confidence, assignments, team scope, live state, model output, or successful persistence. Clearly identify mocks and unavailable API behavior. Never expose Onyx credentials in frontend code. All text Cortex adds is French (Québec). Follow the AI approval boundaries and visual direction in the handoff (model: the ERPNext *Accounting* workspace).

Inspect the actual API contracts and server implementation before representing any flow as production-ready. Update the canonical handoff when implementation truth changes.
