# Cortex ERP AI-Native — Frontend File Ownership & Subagent Protocol

## 1. Subagent Ownership Matrix

To maintain integrity and avoid git collisions during multi-agent collaboration, the frontend directory is partitioned into strictly owned domains:

| Subagent Role | Target Directory / Scope | Responsibilities | Interaction Rules with Other Agents |
|---|---|---|---|
| **Design System Lead** | `src/design-system/**`<br>`src/styles/**` | Design tokens, color system, typography (Inter/JetBrains Mono), base UI components (`CortexButton`, `CortexInput`, `CortexModal`), 7 AI state cards, 5 standard UI state templates | Read-only for other agents. Feature agents import tokens and base components. |
| **App Shell & Navigation Engineer** | `src/app/**`<br>`src/layouts/**`<br>`src/router/**` | App layout, responsive topbar (56px), mobile topbar (64px), collapsible sidebar (248px/72px), mobile bottom nav (64px), breadcrumbs, router guards, provider components | Consumes design system and API client. Provides layout wrappers for feature pages. |
| **Operations UI Engineer** | `src/features/operations/**`<br>`src/features/availability/**`<br>`src/features/rentals/**` | Operations Overview (1), Availability Matrix (2), Rentals List (3), Transaction Composer (4), Rental Detail (5) | Consumes `CortexApiClient`, base components, router params. |
| **Warehouse UI Engineer** | `src/features/checkout/**`<br>`src/features/checkin/**` | Check-out Scanner (6), Check-in Scanner (7), barcode autofocus, audio/haptic feedback, anomaly logging | Consumes `useScanner`, `CortexApiClient`. |
| **Finance & Consignment UI Engineer** | `src/features/consignment/**`<br>`src/features/approvals/**`<br>`src/features/administration/**` | Approval Queue (8), Consignment Dashboard (14), Owner Statement (15), Policies (21), Team (22), Migration (23), Audit Log (24) | Strictly enforces `OwnerStatementSafe` on Screen 15. Consumes `CortexApiClient`. |
| **Intelligence UI Engineer** | `src/features/intelligence/**`<br>`src/features/copilot/**` | Incoming Requests (16), AI Drafts (17), Agent Activity (18), Copilot Sidebar (19), Full Assistant (20) | Consumes 7 canonical AI states, 14 Copilot states, and streaming message contracts. |
| **Platform & Quality Engineer** | Root configs (`package.json`, `vite.config.ts`, `tsconfig.json`, `tailwind.config.ts`, `index.html`)<br>`src/api/**`<br>`src/types/**`<br>`src/i18n/**`<br>`src/utils/**`<br>`src/test/**`<br>`docs/frontend/**` | Architecture setup, `CortexApiClient` & mock layer, Zod validation, `OwnerStatementSafe` sanitizer, i18n subsystem, test harness, quality audits | Exclusively owns root configs, API layer, core types, i18n, utilities, and test suites. |

## 2. Protocol for Cross-Domain Changes
- If a feature engineer needs a new API method or type, they must submit a contract request to `src/api/contracts/` through the Platform & Quality Engineer.
- No direct editing of files outside an agent's assigned ownership scope.
