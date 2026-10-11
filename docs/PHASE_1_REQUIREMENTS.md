# Phase 1 — Product Requirements and Safety Boundaries

**Status:** Requirements baseline committed; implementation starts only after this baseline is reviewed against the repository and delivery constraints.  
**Date:** 2026-10-11  
**Project:** VitalGuard AI — early-warning workflow prototype  
**Current deployment:** https://vitalguard-ai-g215.onrender.com  
**Current API:** https://vitalguard-risk-api.onrender.com/docs

## 1. Product objective

Build a reliable, secure, real-time patient-observation monitoring platform that can accept authorized data, maintain a trustworthy patient timeline, surface transparent risk signals, and support accountable alert workflows. The software must clearly distinguish observed data, missing/stale data, synthetic demonstrations, deterministic scoring, and any future validated predictive model.

A successful deployment does not establish clinical validity. The current deployed application remains a synthetic-data prototype and is not approved for diagnosis, triage, treatment, or patient-care decisions.

## 2. Users and minimum role requirements

These are product requirements, not implemented permissions. All authorization must be enforced server-side in later phases.

| Role | Required access | Explicit restrictions |
|---|---|---|
| System administrator | Manage configuration, users/roles, integrations and operational status | No implicit clinical authority from being an administrator |
| Clinician / authorized care team | View patients assigned to their permitted unit/team; review observations and alerts; acknowledge/escalate according to policy | Cannot access unassigned patient records or change model/system configuration unless separately granted |
| Data-entry / integration operator | Submit or correct observations within an assigned scope; inspect ingestion failures | Cannot approve their own elevated privileges or access unrelated patient records |
| Auditor / quality reviewer | Read permitted audit history, data lineage and approved evaluation reports | Read-only; no clinical actions or record alteration |
| Demo visitor | Use fictional demo scenarios and clearly labelled synthetic views | No real patient data, protected routes, or privileged mutations |

Role names and permissions must be finalized during architecture and security design. Every protected request must be authorized against both role and resource scope; hiding UI controls is not authorization.

## 3. Data classification and source policy

### Allowed during current prototype work
- Clearly synthetic, non-identifiable fixture and simulator data.
- Publicly available documentation and non-sensitive test payloads.
- Authorized, de-identified research datasets only after license/terms, access prerequisites, data-use restrictions, and provenance have been reviewed.

### Prohibited until explicit readiness gates pass
- Identifiable patient information or production hospital data in the current public demo.
- Real patient identifiers in logs, URLs, test fixtures, screenshots, analytics or source control.
- Treating a historical research dataset as a live device feed.
- Using synthetic labels/metrics as evidence of clinical accuracy.

### Future ingestion channels to evaluate
1. Authenticated manual observation entry.
2. Validated CSV/bulk import with preview, row-level errors and an auditable import result.
3. Approved FHIR/HL7 or hospital-system integration.
4. Approved device/gateway integration with source identity and delivery monitoring.

Each record must retain source/provenance, patient/resource mapping, observation time, receipt time, units, validation status and an idempotency/deduplication key where available. Historical dataset ingestion and real-time operational ingestion are separate workflows.

## 4. Required observation contract

Every accepted observation must be validated against a versioned schema. At minimum, the data model must support:
- A stable internal patient reference that is not exposed as a secret or used as authentication.
- Measurement type and numeric value.
- Explicit units and a documented conversion policy.
- Observation timestamp with timezone/offset handling, plus server receipt timestamp.
- Source/system identifier and source record identifier where available.
- Validation/provenance status and correction/retraction history.
- Optional context required by a specific measure, with that context defined before it is used.

Validation must cover malformed payloads, unsupported units, physiologically implausible values, null/missing fields, duplicate delivery, late/out-of-order events, future timestamps, daylight-saving/timezone ambiguity, conflicting corrections, unknown patients, partial imports, oversized payloads and retries after timeout.

A rejected or missing measurement must not be silently replaced with a normal value. Stale or absent data must be represented as unknown/stale, not normal.

## 5. Required application workflows

1. **Secure access:** sign in, session/token lifecycle, role assignment, account disablement and server-side authorization.
2. **Patient worklist:** authorized patient list, ward/team filters, last observation time and data freshness.
3. **Patient detail:** observation timeline, trend history, source/provenance and missing-data indicators.
4. **Ingestion:** validated entry/import, preview, idempotent retries, per-record outcomes and error recovery.
5. **Risk signal:** identify the exact algorithm/version, inputs, timestamps, missingness and limitations behind each output.
6. **Alert operations:** deduplication, acknowledge, resolve, escalation, assignment, reason/comment where required, and immutable audit history.
7. **Realtime updates:** explicit connection state, reconnect/replay strategy, ordering and visible degraded-state handling.
8. **Operations:** health/readiness status, request correlation IDs, privacy-safe logs, delivery failures, backups, restore drills and release rollback.
9. **Governance:** data retention, access review, incident process, dataset/model versioning and documented release approval.

## 6. Risk-score and clinical-safety requirements

- Keep rule-based scores (such as a NEWS2 demonstration) distinct from ML model outputs.
- Never call a synthetic model score a clinically validated probability.
- Do not label coefficient contributions as SHAP or causal explanations.
- For a future model, specify intended population, outcome definition, prediction horizon, index time, exclusions, handling of missing data and action threshold before training/evaluation.
- Prevent leakage across patients and time; use patient/time-aware splits and independent evaluation.
- Report calibration and clinically relevant metrics with confidence intervals, subgroup analysis, and limitations. Choose thresholds with clinical stakeholders; do not optimize accuracy alone.
- Require independent review against the authoritative clinical specification for any clinical scoring implementation.
- A model or score must not independently trigger treatment. Human review, escalation policy, usability testing and safety case are required before any controlled pilot.
- Missing, stale, conflicting or out-of-range data must be visible and must not be treated as reassuring evidence.

## 7. Privacy, security and audit requirements

- No real patient data before identity, resource-level authorization, secure storage, secrets management and governance gates are approved.
- Least privilege, deny-by-default access, session expiration/revocation and auditable privileged actions.
- TLS in transit and appropriately managed encryption at rest for any future sensitive deployment.
- Validate input and constrain payload size/rate; protect against injection, cross-origin abuse, CSRF where applicable, broken object-level authorization and sensitive error leakage.
- Do not log credentials, tokens, direct identifiers or full sensitive payloads.
- Define retention, deletion, export, backup and restore behavior before onboarding sensitive data.
- Record who performed a sensitive action, what changed, when, target resource, and outcome; protect audit history from ordinary alteration.
- Secrets must never be committed or placed in browser-exposed `VITE_*` variables.

## 8. Non-functional requirements

- Reliable API contracts, bounded timeouts and clear error states.
- Duplicate-safe ingestion and recoverable transient failures.
- Time-aware event ordering and a visible last-successful-update timestamp.
- Accessibility, responsive layouts and understandable empty/loading/error states.
- Automated unit, integration, authorization, migration, frontend and end-to-end tests.
- Reproducible builds, pinned dependencies, dependency/security checks and tested rollback.
- Observability without exposing sensitive information.
- Backup/restore and data retention procedures with verifiable recovery objectives.
- Performance targets and concurrency/load expectations must be measured and set before production release.

## 9. Explicitly out of scope for current demo

- Clinical diagnosis, triage, treatment recommendation or autonomous intervention.
- Claims of clinical accuracy, regulatory approval, NEWS2 certification or validated SHAP explanations.
- Ingestion of live hospital/device data without an approved integration and authorization.
- Production use of the current synthetic model.
- Claiming that historical datasets constitute live monitoring.
- Marketing the system as production-ready solely because a Render deployment is live.

## 10. Acceptance criteria for Phase 1

- [x] Product objective and current safety boundary documented.
- [x] User classes and required access restrictions documented.
- [x] Data source rules and future ingestion options documented.
- [x] Observation validation and edge-case expectations documented.
- [x] Core user workflows and audit expectations documented.
- [x] Risk-score/model validity requirements documented.
- [x] Privacy/security and non-functional requirements documented.
- [x] Explicit out-of-scope items documented.
- [ ] Requirements mapped to versioned API contracts and data model in Phase 2.
- [ ] Security and persistence implementation delivered and tested in later phases.
- [ ] Clinical/safety/privacy readiness reviewed independently before any patient-care use.

## 11. Decisions that must remain open until evidence exists

- Exact identity provider and authentication protocol.
- Final role-to-permission matrix and patient/ward tenancy model.
- Approved data sources, legal basis, licensing and retention period.
- Managed database provider and recovery objectives.
- Model target, prediction horizon, acceptable calibration/performance and escalation thresholds.
- Notification channels and clinical escalation ownership.
- Applicable privacy, medical-device and healthcare compliance obligations for the deployment jurisdiction.

These decisions must be resolved with the relevant system owner, security/privacy reviewers, data providers and qualified clinical stakeholders; they must not be guessed in code.
