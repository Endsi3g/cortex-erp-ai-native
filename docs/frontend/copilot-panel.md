# Cortex Copilot Panel

A floating, non-modal chat panel mounted on every Desk page, plus a
detached full-page version at `/app/cortex-assistant`. Built against
the **real** `cortex_rental.api.v1.chat` endpoints from the seventh
wave (`CHANGELOG.md`) — not client-side mock data — so this is a real
integration of the chat gateway, even though that gateway itself still
talks to `MockOnyxChatClient`, not a live Onyx.

## Files

```
apps/cortex_rental/cortex_rental/public/js/cortex_copilot/
├── chatClient.js                 # real frappe.call() wrapper for api/v1/chat.*
├── CortexCopilotPanel.vue        # root: floating or docked mode
├── CopilotHeader.vue
├── CopilotContextBar.vue
├── CopilotQuickActions.vue
├── CopilotConversation.vue       # dispatches each block to its renderer
├── CopilotComposer.vue
├── CopilotVerifiedFact.vue       # renders ChatBlock.type == "verified_fact"
├── CopilotExtractedData.vue      # "extracted_data"
├── CopilotProposalCard.vue       # "proposal"
├── CopilotApprovalCard.vue       # "approval_required"
├── CopilotRiskCard.vue           # "risk"
├── CopilotMissingInfoCard.vue    # "missing_information"
├── CopilotToolProgress.vue       # "tool_progress"
├── CopilotErrorCard.vue          # "error"
└── cortex_copilot.bundle.js      # global mount (app_include_js)

apps/cortex_rental/cortex_rental/public/js/cortex_assistant/
└── cortex_assistant.bundle.js    # mounts CortexCopilotPanel mode="docked"

apps/cortex_rental/cortex_rental/cortex_rental/page/cortex_assistant/
└── cortex_assistant.json / .js   # the /app/cortex-assistant Desk Page
```

`BLOCK_COMPONENTS` in `CopilotConversation.vue` is the single mapping
from the backend's `ChatBlock` discriminator (`schemas/chat_schemas.py`)
to a renderer — the eight component names above match the eight real
block types exactly, not the (slightly different) component list from
the original design spec, since the real backend contract from the
seventh wave is the authority here, not the earlier draft prompt.

## Global mount — verified pattern, not guessed

`hooks.py`'s `app_include_js` points at `cortex_copilot.bundle.js`,
which calls `frappe.ready()` (real, documented Frappe lifecycle hook)
to mount the launcher once the Desk shell is up. `app_include_js`
resolving a `.bundle.js` with ESM imports through the same esbuild
pipeline that compiles a Desk Page's own bundle is a real, cross-
checked pattern (see `CHANGELOG.md`, eighth wave, for the two searches
that confirmed it) — not assumed from the Desk-Page pattern alone.

The launcher hides itself for `Guest` and for any identity holding none
of the `HUMAN_STAFF_ROLES` (a client-side courtesy only — the server
gate is `require_human_staff_role()` on every endpoint in
`api/v1/chat.py`, unaffected by whether this check runs or is accurate).

## What's real vs. disclosed simplification

| Behavior | Status |
|---|---|
| Sending a message → real `send_message` call → real DocType rows created | Real |
| `SendMessageRequest` rejecting a client-supplied `company`/`agent`/`model` | Real (same Pydantic contract as the backend tests) |
| Context resolution (`resolveDeskContext()`) | Real for `Form` routes and `/app/cortex-availability`; falls back to `dashboard` for every other route (Check-in/Consignment/Approvals pages don't exist yet) |
| Quick actions | Only defined for pages `resolveDeskContext()` can actually produce — no button pretends a not-yet-built screen exists |
| Proposal (`CopilotProposalCard`) / Approval (`CopilotApprovalCard`) primary actions | Proposal's button re-sends its own title as the next chat message (a real round-trip through the real pipeline) — there is no Transaction Composer yet to open prefilled. Approval's button navigates to the real `Approval Request` Frappe Form (`frappe.set_route`), which does exist today. Neither fabricates a mutation that isn't actually wired. |
| Context bar "Modifier le contexte" editor | **Not built.** The bar is read-only in this pass — no drawer for toggling which context is shared. |
| Live context reactivity while the panel stays open across navigation | **Not built.** Context is recomputed when the panel opens and before each send, not on every route change — no verified low-risk Frappe router-change event was used for this pass (disclosed rather than guessed at). |
| Panel width persistence | Plain `localStorage` per browser (not per Frappe user profile) — a real per-viewer convenience, not a synced preference. |
| Streaming responses | **Not built.** `send_message` is a single request/response call, matching the backend's current synchronous implementation (seventh wave). |
| Dark mode | Inherits the design system's light-mode-only state (fifth/sixth wave) — untested in dark. |

## Accessibility

- The floating panel is `role="complementary"`, non-modal: background
  Desk content stays interactive, Tab is never trapped.
- `Escape` closes the floating panel (not the docked page) and returns
  focus to the launcher button.
- `⌘J`/`Ctrl+J` toggles the panel from anywhere (a modifier combo,
  deliberately not gated behind "not currently in a text field" the
  way single-letter shortcuts elsewhere in this spec are, since it
  can't collide with normal typing).
- Every icon-only button (`✕`, `↗`) carries `aria-label` and `title`.
- The conversation region is `role="log" aria-live="polite"` so new
  assistant messages are announced without re-reading the whole thread.
- Focus-visible ring, contrast, and color+icon+text rules are inherited
  from the design system (`docs/design-system.md`) — no new tokens or
  overrides introduced here.

## Not done in this pass

Tracked in `HANDOFF.md`: streaming, a real context editor, live route-
change reactivity, wiring proposals to an actual Transaction Composer
once one exists, and a real Onyx client to replace the mock this panel
is currently, honestly, talking to.
