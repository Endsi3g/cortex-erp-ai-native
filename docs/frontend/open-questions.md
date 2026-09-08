# Cortex ERP AI-Native — Frontend Architecture Open Questions & Decisions

## 1. Technical & Architectural Decisions (Resolved)

| ID | Topic | Decision | Justification |
|---|---|---|---|
| **ADR-01** | API Communication Boundary | Typed `CortexApiClient` with concrete `HttpCortexApiClient` and development `MockCortexApiClient`. | Ensures 100% decoupling from backend implementation details and allows full demo simulation without running Frappe bench. |
| **ADR-02** | Privacy Boundary on Consignment | Strict `OwnerStatementSafe` TypeScript interface and runtime recursive sanitization. | Guarantees zero leakage of renter contact, payment, discounts, or project details to third-party equipment owners. |
| **ADR-03** | Currency & Date Localization | Dedicated `formatters.ts` supporting `fr-CA` (`1 920,00 $`) and `en-CA` (`$1,920.00`). | Aligns with Canadian bilingual requirements and Quebec French standard conventions. |
| **ADR-04** | Idempotency & Concurrency | `Idempotency-Key` header with UUID v4 on all mutations, plus `ETag` / `version` comparison for stale detection. | Prevents duplicate charges/reservations from double clicks and guards against dirty writes. |
| **ADR-05** | High-Speed Warehouse Scanning | 52px input with persistent autofocus, visual toast, subtle Web Audio tone, and vibration feedback. | Maximizes warehouse technician throughput during prep and check-in without cognitive clutter. |

## 2. Open Items for Backend Integration (Gate 2 / Gate 3)

| ID | Question / Requirement | Target Subsystem | Proposed Resolution |
|---|---|---|---|
| **OQ-01** | WebSocket / Server-Sent Events for Availability Matrix real-time updates. | Frappe Redis Queue / Socket.io | Hook Frappe Socket.io events to `CortexApiClient.onAvailabilityChange()` in Gate 2. |
| **OQ-02** | S3 / MinIO pre-signed URL generation for damage evidence photos. | Frappe File Manager / S3 Adapter | `CortexApiClient.createUploadIntent()` returning signed PUT URL + server-side SHA-256 validation. |
| **OQ-03** | PDF generation of `OwnerStatementSafe` on server. | Frappe Print Format / Weasyprint | Server-side PDF template consuming the exact sanitized JSON structure of `OwnerStatementSafe`. |
