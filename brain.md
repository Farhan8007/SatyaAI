# SATYA AI — System Architecture & Security Lead Working Document

## 1. Architecture Summary
- **Stack**: FastAPI (Python 3.12, Motor async MongoDB), Next.js 14 (App Router, Tailwind, Recharts), scikit-learn Isolation Forest, ReportLab.
- **Layout**: `backend/app/` (routers, security, models, services, ai) + `frontend/` (Next.js app/components/lib) + root `docker-compose.yml`.
- **Auth**: JWT bearer auth with bcrypt; roles: `administrator`, `paper_setter`, `moderator`, `examination_centre`, `security_auditor`.
- **Papers Lifecycle**: Setters upload content (AES-256 encrypted, SHA-256 hashed, RSA-PSS signed) -> Moderator approves -> Exam Centre unlocks.
- **AI & Audit Connection**: Every sensitive API action triggers `record_audit_log()`, appending to a SHA-256 hash chain with 9 behavioral features; entries are immediately scored by an Isolation Forest (`ai/anomaly_detector.py`); if risk >= 35, `ai/explainer.py` extracts plain-language reasons into `alerts` for auditor review and PDF incident report generation (`ai/report_generator.py`).

## 2. Current State Table

| File | What It Does (Verified from Code) | Status |
|---|---|---|
| `backend/app/routers/auth.py` | Handles user signup (single-admin check), email verification token flow, and login with bcrypt check, active validation, and login audit emission. | Working |
| `backend/app/routers/papers.py` | Paper lifecycle (upload, list, approve/reject, unlock, download); **Day 3**: Decrypt+verify+stream download; **Day 5**: release-window enforcement in `unlock_paper` (rejects early unlocks with `PREMATURE_UNLOCK_ATTEMPT` audit event). | Working |
| `backend/app/routers/alerts.py` | Lists AI-generated security alerts with optional resolution filter; allows auditors/admins to mark alerts resolved. | Working |
| `backend/app/routers/audit.py` | Fetches filtered audit logs (user/action) and exposes `/verify-integrity` to recompute and validate the SHA-256 hash chain. | Working |
| `backend/app/routers/users.py` | Admin user CRUD: list, role reassignment, account deletion; fixed `toggle_status` to persist `is_active`, block self-suspension, and log audit. | Working |
| `backend/app/routers/reports.py` | Aggregates alert and audit data into structured incident investigations; persists reports and streams dynamic ReportLab PDF binaries. | Working |
| `backend/app/routers/dashboard.py` | Aggregates system metrics (paper totals, pending approvals, today's logins, active alerts, avg risk score, recent logs) for overview UI. | Working |
| `backend/app/security/auth_utils.py` | JWT + bcrypt + `require_roles` RBAC; **Day 2**: `get_current_user` re-fetches from MongoDB (rejects deleted/suspended users immediately); added `verify_paper_access` subject/centre scoping helper. | Working |
| `backend/app/security/encryption.py` | AES-256-CBC, SHA-256 chain hashing, RSA-PSS sign/verify; **Day 2**: RSA keys persisted via configurable `RSA_KEYS_DIR` / PEM paths, never regenerate if files exist; AES key validated for 32-byte minimum. | Working |
| `backend/app/services/audit_service.py` | Hash-chained audit log writer with inline AI anomaly scoring; **Day 2**: read→hash→insert critical section serialized with loop-safe `asyncio.Lock` preventing concurrent forks; `verify_chain()` and `verify_chain_integrity()` confirmed. | Working |

## 3. Member 2 (Security Lead) Implementation Plan

### Day 1: Security Audit Findings
- **Files**: `backend/app/security/auth_utils.py`, `backend/app/security/encryption.py`, `backend/app/routers/papers.py`
- **What's Missing / Findings**:
  - `auth_utils.py`: `get_current_user` decodes token payload without DB lookup. Suspended/deleted users remain authenticated until JWT expires. RBAC checks role name only; no resource or subject/centre scoping.
  - `encryption.py`: RSA keys generated ephemerally at runtime (`rsa.generate_private_key()`); restarting the backend invalidates all past paper signatures. AES key is a static single secret truncated to 32 bytes from `.env` without envelope encryption or key rotation.
  - `papers.py`: No download endpoint exists (`GET /api/papers/{id}/download`). `POST /{id}/unlock` only returns a status string; never decrypts, validates signatures, or streams paper bytes. No centre assignment checks.
- **Acceptance Test**: Audit script asserts: (1) suspended user JWT is rejected via DB check; (2) server restart does not destroy RSA verification capability; (3) missing download route is flagged and documented.

### Day 2: Scoping Gaps, Key Persistence & Audit-Chain Concurrency
- **Files**: `backend/app/security/auth_utils.py`, `backend/app/security/encryption.py`, `backend/app/services/audit_service.py`, `backend/app/models/paper.py`
- **What's Missing**:
  - Fine-grained RBAC: Add `get_current_active_user` (DB check) and `require_paper_access` dependency ensuring setters only see own papers and exam centres only see papers assigned to their centre.
  - Key persistence: Load RSA keys from persistent PEM files or environment variables (generate and persist to disk on first run if missing); enforce valid 32-byte AES key validation.
  - Audit-chain concurrency: `record_audit_log()` reads `last_hash` then inserts without locking; concurrent requests create forked chains with identical `prev_hash`, breaking `/verify-integrity`. Implement `asyncio.Lock()` to serialize chain hashing.
- **Acceptance Test**:
  - Concurrency: `asyncio.gather()` executing 50 simultaneous `record_audit_log` writes; `verify_chain_integrity()` passes with 100% linear validity.
  - Persistence: Sign sample payload, restart backend process, verify signature passes with reloaded keys.
  - Scoping: Exam Centre A receives HTTP 403 when requesting paper assigned to Exam Centre B.

### Day 3: Decrypt + Verify + Stream Download & Release Checks
- **Files**: `backend/app/routers/papers.py`, `backend/app/security/encryption.py`, `backend/app/security/auth_utils.py`
- **What's Missing**:
  - Implement `GET /api/papers/{paper_id}/download` endpoint.
  - Verification & Decryption: Fetch `encrypted_blob`, verify paper status == `approved`, verify caller is authorized assigned centre (or admin), decrypt AES-256 blob, recompute SHA-256 hash to confirm match with `paper.sha256_hash`, and verify RSA signature with public key.
  - If tamper or signature check fails: abort with HTTP 400/409, emit `TAMPER_DETECTED` critical audit log triggering AI anomaly alert.
  - If valid: stream decrypted bytes via `StreamingResponse` and log `DOWNLOAD_PAPER` with `status="SUCCESS"`.
- **Acceptance Test**: Upload file -> approve -> call download as assigned centre -> verify returned bytes match original file bit-for-bit, hash matches, and audit log recorded.

### Day 5: Release-Window Enforcement Tie-In
- **Files**: `backend/app/routers/papers.py`, `backend/app/models/paper.py`, `backend/app/services/audit_service.py`
- **What's Missing**:
  - Add `unlock_window_minutes` (default: 30 mins) and `exam_end_time` to paper schema.
  - In `unlock_paper` and `download_paper`, check `datetime.utcnow()` against `[exam_date - unlock_window, exam_end_time]`.
  - Block attempts outside window with HTTP 403 ("Exam release window not open / has expired").
  - Record audit log with `action="UNAUTHORIZED_TIME_ACCESS"` and set high risk score / alert trigger for early access attempts.
- **Acceptance Test**:
  - Request download at `T - 60m` (window = 30m) -> receives HTTP 403 Forbidden; verify alert triggered in `/api/alerts`.
  - Request download at `T - 15m` -> receives HTTP 200 OK with decrypted stream.

### Day 8: Negative Security Test Suite
- **Files**: `backend/tests/test_security.py` (new test suite using pytest + httpx `AsyncClient`)
- **What's Missing**:
  - Automated security regression test coverage for all negative security paths.
  - Test cases:
    1. Unauthorized role access: Setter attempting to approve; Exam Centre attempting upload; unauthenticated requests.
    2. Centre isolation: Exam Centre querying/downloading papers assigned to another centre.
    3. Premature access: Download request before unlock window opens (asserts 403 + security alert creation).
    4. Tampered ciphertext: Corrupt 1 byte in MongoDB `encrypted_blob` -> download triggers integrity failure + `TAMPER_DETECTED` audit log.
    5. Invalid signature: Corrupted RSA signature rejected during download verification.
    6. Suspended user: Suspended user token rejected immediately on protected endpoints.
- **Acceptance Test**: `pytest backend/tests/test_security.py -v` passes 100% with all negative vectors returning expected 401/403/409 codes and correct audit events.

## 4. Open Questions & Assumptions Needing Confirmation
- **Q1 (RSA Architecture)**: Institutional master keypair vs. per-setter personal RSA keypairs? Stored on disk (`.pem`), AWS KMS/Vault, or DB keystore?
- **Q2 (Symmetric Encryption)**: Retain single global AES-256 key from `.env` or move to envelope encryption (per-paper DEK encrypted under master KEK)?
- **Q3 (Centre Assignment)**: Can multiple examination centres be assigned to one paper (`exam_centres: list[str]`), and who assigns them (setter at upload or moderator during review)?
- **Q4 (Download Policy)**: Is paper download unlimited during the release window, or strictly single-use / requires 2FA or OTP confirmation per centre?
- **Q5 (Payload Storage)**: Store encrypted blobs directly in MongoDB documents (16MB BSON limit), MongoDB GridFS, or encrypted local/S3 object storage?
- **Q6 (Distributed Concurrency)**: For audit log chaining, is in-process `asyncio.Lock` acceptable (single-worker backend), or is a Redis distributed lock / DB transaction required for multi-worker scaling?
