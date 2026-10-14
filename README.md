# SATYA AI — Examination Forensic Intelligence & Secure Audit System

An AI-powered platform that secures question papers across their entire
lifecycle and explains, in plain language, exactly what happened when
something goes wrong.

> **Status: Checkpoint 13 — motion and richer color.** Added
> `framer-motion` entrance animations (staggered stat cards, fade-up
> sections), a sliding animated active-nav indicator in the sidebar
> (shared `layoutId` transition), gradient icon chips per stat card
> (indigo/teal/violet/amber/rose), animated floating gradient orbs on
> the landing/login/signup pages, and hover-lift/glow shadows on cards.
> All done through shared components and design tokens, so it applies
> consistently rather than one-off per page. All 12 routes rebuilt and
> verified with zero errors.

> **Status: Checkpoint 12 — light, card-based theme.** The app moved from
> its original dark theme to a light theme with a solid indigo sidebar,
> white rounded cards, and soft shadows -- the "light mode" item that was
> on the original brief since the very first checkpoint. Every page
> inherits the new look through shared design tokens and component
> classes (`.glass-card`, `.btn-primary`, etc.) rather than one-off
> per-page styling, so the whole app stayed visually consistent in one
> pass. All 12 routes rebuilt and verified with zero errors.
> Two real bugs fixed and verified with actual live-server HTTP requests
> (not just unit tests): (1) MongoDB's default 30-second connection
> timeout meant the whole app appeared to "hang" whenever the database
> was unreachable -- now capped at 5 seconds. (2) An unhandled server
> error (like that same MongoDB outage) was escaping before CORS headers
> could be attached to the response, so the browser reported a confusing
> "blocked by CORS policy" error that hid the real problem. A correctly
> ordered error-catching middleware now returns a clear, honest message
> instead -- confirmed by inspecting the actual HTTP response headers
> from a live server, not assumed from reading the code.

---

## 1. Architecture

```
                     ┌───────────────────────┐
                     │      Next.js UI        │
                     │  (dashboard, login,    │
                     │   landing page)        │
                     └──────────┬────────────┘
                                │ REST (JWT bearer)
                     ┌──────────▼────────────┐
                     │      FastAPI            │
                     │  routers: auth, papers, │
                     │  audit, alerts,         │
                     │  dashboard, reports     │
                     └───┬─────────────┬──────┘
                         │             │
              ┌──────────▼───┐   ┌─────▼─────────────┐
              │   MongoDB     │   │   AI Engine        │
              │ users, papers,│   │ Isolation Forest → │
              │ audit_logs,   │◄──┤ risk score →       │
              │ alerts,       │   │ rule-based         │
              │ reports       │   │ explainer →        │
              └───────────────┘   │ report generator   │
                                  └────────────────────┘
```

**Examination workflow implemented end-to-end:**
Create → AES-256 Encrypt → SHA-256 Hash → RSA Digital Signature → Approval
(Moderator) → Tamper-evident, hash-chained Audit Log → AI Monitoring →
Timed Exam-Centre Unlock → Post-exam Investigation Report (PDF).

## 2. Tech stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14 (App Router), TypeScript, Tailwind CSS, Recharts, lucide-react |
| Backend | FastAPI (Python 3.12), Motor (async MongoDB driver) |
| Database | MongoDB |
| Auth | JWT (python-jose) + bcrypt (passlib) |
| AI / ML | scikit-learn Isolation Forest, pandas, numpy, rule-based explainability layer |
| Security | AES-256 (CBC), SHA-256, RSA-PSS digital signatures |
| Reports | reportlab (PDF generation) |
| Sample data | Faker — 20 users, 40 papers, 500+ chained audit logs, ~60 AI alerts |
| Deployment | Docker + docker-compose |

## 3. Project layout

```
satya-ai/
├── backend/
│   └── app/
│       ├── main.py                # FastAPI entrypoint
│       ├── config.py              # Settings (env-driven)
│       ├── database.py            # MongoDB connection + collections
│       ├── models/                # Pydantic schemas (user, paper, audit_log, alert)
│       ├── routers/               # auth, users, papers, audit, alerts, dashboard, reports
│       ├── security/              # auth_utils.py (JWT/bcrypt), encryption.py (AES/SHA/RSA)
│       ├── ai/                    # anomaly_detector.py, explainer.py, report_generator.py
│       └── services/              # audit_service.py (hash-chained log writer), seed_data.py
├── frontend/
│   └── app/                       # landing, /signup, /login, /dashboard (+ papers, alerts, audit-logs, reports, users, settings)
│       components/                # Sidebar, StatCard, RiskBadge, StatusBadge
│       lib/api.ts                 # API client (falls back to mock data if backend is offline)
├── docker-compose.yml
└── docs/
```

## 4. Running locally

### Backend

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                 # edit JWT_SECRET / AES_SECRET_KEY for real use
# start MongoDB locally, or: docker run -p 27017:27017 mongo:7

python -m app.services.seed_data     # generates users, papers, 500+ audit logs, AI alerts
uvicorn app.main:app --reload        # http://localhost:8000
```

Demo logins after seeding (password for all: `Password@123`):
`administrator@satyaai.demo`, `paper_setter@satyaai.demo`,
`moderator@satyaai.demo`, `examination_centre@satyaai.demo`,
`security_auditor@satyaai.demo`.

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev                          # http://localhost:3000
```

The dashboard works even before the backend is running — `lib/api.ts` falls
back to realistic mock data so the UI is always demoable.

### Everything via Docker

```bash
docker-compose up --build
# then in a separate shell, seed the database:
docker exec -it satya-backend python -m app.services.seed_data
```

## 5. Database schema (MongoDB collections)

**users** — `id, name, email, role, institution, hashed_password, created_at, last_login, is_active, failed_login_count, known_devices[], known_ips[]`

**papers** — `id, title, subject, exam_date, exam_centre, setter_id, setter_name, status (pending/approved/rejected), sha256_hash, signature, is_encrypted, encrypted_blob, created_at, remarks`

**audit_logs** — `id, timestamp, user_id, user_name, role, ip_address, location, device, browser, action, paper_id, status, hash, prev_hash` (+ engineered features: `hour_of_day, is_new_device, is_new_ip, is_failed_login, downloads_last_hour, locations_last_24h, is_bulk_download, skipped_approval, permission_escalation`)

Each entry's `hash` is `SHA256(prev_hash + entry_data)` — a hash chain, so
altering any past entry breaks every hash after it. `GET /api/audit-logs/verify-integrity`
recomputes the whole chain to detect tampering.

**alerts** — `id, created_at, user_id, user_name, risk_score (0-100), risk_level, reasons[], confidence, recommended_action, related_paper_id, related_log_ids[], resolved`

**reports** — output of `build_incident_report()`: `incident_id, generated_at, summary, timeline[], users_involved[], affected_paper, risk_level, contributing_factors[], recommended_action`

## 6. API summary

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/auth/signup` | Register a user (any role); sends a verification email if SMTP is configured |
| GET | `/api/auth/verify-email?token=...` | Verifies the email from the link sent on signup |
| POST | `/api/auth/login` | Login → JWT; records LOGIN audit log + new-device/IP detection |
| GET | `/api/users/` | List all users (Administrator only) |
| PATCH | `/api/users/{id}/role` | Reassign a user's role (Administrator only) |
| PATCH | `/api/users/{id}/status` | Suspend / reactivate a user (Administrator only) -- suspended users are now actually blocked from logging in |
| DELETE | `/api/users/{id}` | Remove a user entirely (Administrator only); frees up their email to be reinvited. Blocked for the Administrator role and for deleting yourself |
| POST | `/api/papers/upload` | Paper Setter uploads → hashed, signed, AES-encrypted |
| GET | `/api/papers/` | List papers |
| POST | `/api/papers/{id}/approve` \| `/reject` | Moderator decision |
| POST | `/api/papers/{id}/unlock` | Exam Centre timed unlock (blocked unless approved) |
| GET | `/api/audit-logs/` | Filterable audit trail |
| GET | `/api/audit-logs/verify-integrity` | Recomputes the hash chain |
| GET | `/api/alerts/` | AI-generated alerts (risk score + explanation) |
| POST | `/api/alerts/{id}/resolve` | Security Auditor marks resolved |
| GET | `/api/dashboard/summary` | All dashboard stats + recent alerts + activity feed |
| POST | `/api/reports/incident/{alert_id}` | Generates a structured investigation report |
| GET | `/api/reports/incident/{id}/pdf` | Downloads the report as PDF |

Interactive docs: `http://localhost:8000/docs` (Swagger, auto-generated by FastAPI).

## 7. How the AI actually works

1. **Feature engineering** — every audit log entry carries 9 behavioural
   features (unusual hour, new device, new IP, failed login, download
   burst, multi-location access, bulk download, skipped approval,
   permission escalation).
2. **Isolation Forest** (`ai/anomaly_detector.py`) is trained on the full
   log history and scores each new entry; its raw anomaly score is mapped
   to an intuitive **0–100 risk score**.
3. **Explainability layer** (`ai/explainer.py`) is a transparent, rule-based
   pass over the *same* feature row — it never invents a reason; it only
   surfaces which of the 9 signals actually fired, in plain language, plus
   a confidence estimate and a recommended action. This is what makes every
   alert explainable rather than a black box.
4. **Report generator** (`ai/report_generator.py`) narrates only facts
   already present in the audit log and alert — it summarizes, it does not
   fabricate timeline events.

## 8. What's next (future checkpoints)

- Command palette, keyboard shortcuts, realtime updates (websockets).
- Light mode + full animation pass (Framer Motion page transitions).
- Unit tests for the AI scoring/explainability logic and the hash-chain
  verifier.
- Docker Compose smoke test (spin up mongo + backend + frontend together).
- Wire the Reports page to list *all* generated reports, not just the one
  just-generated incident (currently reads the `?incident=` query param).
- Password reset flow for invited users (currently issued a temp password
  with no reset endpoint yet).
