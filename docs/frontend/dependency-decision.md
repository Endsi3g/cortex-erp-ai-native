# Cortex ERP AI-Native — Frontend Dependency Decision Record

## 1. Context & Objectives
The Cortex ERP frontend requires a modern, robust, type-safe stack designed for operational speed, high-density workflows, accessible UI, and clean boundary separation from the Frappe Framework backend.

## 2. Selected Technologies & Rationale

| Category | Selected Library | Version | Rationale & Alternatives Considered |
|---|---|---|---|
| **Core Framework** | `vue` | `^3.4.38` | Modern Composition API (`<script setup lang="ts">`), fine-grained reactivity, optimal performance for real-time dashboards and scanners. |
| **Language** | `typescript` | `^5.5.4` | Strict type checking (`noImplicitAny: true`, `strictNullChecks: true`, zero `any` policy), enhanced IDE auto-completion, compile-time contract enforcement. |
| **Build Tooling** | `vite` | `^5.4.2` | Lightning-fast HMR, optimized Rollup bundling, native ES module support, seamless Vitest integration. |
| **Styling** | `tailwindcss` | `^3.4.10` | Utility-first CSS mapped strictly to "Cortex OS — Operational Green" design tokens, tree-shaken minimal bundle size, responsive breakpoints. |
| **State Management** | `pinia` | `^2.2.2` | Type-safe, modular, lightweight reactive stores for session, tenant company context, navigation, and Copilot states. |
| **Routing** | `vue-router` | `^4.4.3` | SPA declarative routing, strongly-typed route metadata, async chunk loading for the 24 canonical screens, navigation guards. |
| **Internationalization** | `vue-i18n` | `^9.13.1` | Native bilingual support (`fr-CA` / `en-CA`), pluralization, currency and date formatting hooks. |
| **Schema Validation** | `zod` | `^3.23.8` | Runtime schema validation for API responses, form inputs, and `OwnerStatementSafe` sanitizer boundaries. |
| **Virtualization** | `@tanstack/vue-virtual` | `^3.8.4` | Virtualized rendering for large datasets (>100 rows in Availability Matrix and Rentals List) to ensure smooth 60fps scrolling. |
| **Icons** | `lucide-vue-next` | `^0.438.0` | Consistent, lightweight, accessible SVG icon set matching operational ERP actions and 7 AI states. |
| **Unit & Integration Testing** | `vitest` + `@vue/test-utils` + `happy-dom` | `^2.0.5` | Fast in-memory testing, full DOM simulation, native Vite config sharing, coverage reporting. |
| **E2E Testing** | `@playwright/test` | `^1.46.1` | Cross-browser automated validation of the 5 transversal workflows and responsive viewports (1440, 1280, 768, 390). |
| **Accessibility Auditing** | `axe-core` + `@axe-core/vue` | `^4.9.1` | Automated WCAG 2.2 AA compliance validation in test harnesses. |

## 3. Boundary Rules & Prohibitions
- **No direct HTTP `fetch` in Vue components**: All backend interactions must pass through `CortexApiClient`.
- **No client-side calculations of official pricing or availability**: Backend Frappe/ERPNext services are the sole authority.
- **Strict `DEMO-` prefixing**: Synthetic test fixtures must never be confused with live production records.
- **Zero Renter PII in Consignment**: Consignment statements must strictly adhere to `OwnerStatementSafe`.
