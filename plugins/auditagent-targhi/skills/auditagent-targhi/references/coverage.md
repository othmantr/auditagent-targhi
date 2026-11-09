# Adaptive audit coverage

Report each area as inspected-static / tested-local / tested-staging / unverified / not-applicable, with evidence and gaps. Inspect applicable areas, not a universal tool checklist.

| Area | Questions |
|---|---|
| Product and scope | Critical journeys, intended scale, maturity, business rules, explicit non-goals? |
| Architecture | Module boundaries, coupling, duplication, dependency direction, dead code evidence, maintainability? |
| Security | Authentication, recovery, sessions, authorization per resource, tenant isolation, injection/XSS/CSRF/SSRF, uploads, secrets, abuse, dependencies, OAuth, webhooks? |
| Data | Constraints, transactions, concurrency, indexes/query shapes, retention/export/deletion, migrations/backward compatibility, tested recovery? |
| Reliability | Idempotency, retries/backoff, DLQ, timeout, reconciliation, external failure isolation, scheduling/timezones, monitoring, logs/traces? |
| Delivery | Builds/tests, artifact provenance, configuration separation, safe rollout, rollback limits, documentation, infrastructure access? |
| UX/accessibility | Real rendered journeys if tools available, loading/empty/error/offline, keyboard/focus, semantics, contrast, RTL/locales, responsive layouts? |
| Mobile | Local protected storage, offline persistence/sync conflicts, app lifecycle, permissions, deep links, API backward compatibility, update constraints? |
| Billing/AI | Entitlements enforced server-side, metering, atomic credit accounting, duplicate events, cost/concurrency caps, model failure behavior, evaluation set, prompt/tool trust boundaries? |
| Operations | Support/admin least privilege, audit trails, incident response, RTO/RPO evidence, ownership/runbooks, capacity and per-customer cost? |

Use OWASP ASVS as a source of applicable web security requirements, MASVS/MASTG for mobile, and API Security guidance for API risks. These are references, not automatic certifications. Fetch current primary documentation for version-specific recommendations. Never test third-party targets or production without explicit authorization. Dependency directories excluded from snapshots still require manifest/lockfile/version review.
