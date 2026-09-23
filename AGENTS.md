# Instructions for AI agents working in Cortex

Before changing the product UI, read [`docs/frontend/CORTEX_UI_HANDOFF_V2.md`](docs/frontend/CORTEX_UI_HANDOFF_V2.md). It is the canonical frontend/product contract for every agent and supersedes older frontend descriptions in `HANDOFF.md`.

Keep ERPNext/Frappe as the system of record; use Frappe UI first; send all writes through permission-checked Frappe domain APIs. Do not invent confidence, assignments, team scope, live state, model output, or successful persistence. Clearly identify mocks and unavailable API behavior. Never expose Onyx credentials in frontend code. Follow the AI approval boundaries and visual direction in the handoff.

Inspect the actual API contracts and server implementation before representing any flow as production-ready. Update the canonical handoff when implementation truth changes.
