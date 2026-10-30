# PromptwarsxAstra — CivicAction Karnataka 🏛️

> **AI for Civic Impact (PromptWars × ASTRA Hackathon Prototype)**  
> Transform unstructured, multilingual citizen complaints into deduplicated, prioritized, and trackable municipal action — even across low-connectivity Western Ghats and forest regions.

---

## 🌟 Key Highlights

- ⚡ **Groq LLM Triage (`openai/gpt-oss-20b`):** Extraction of categories, summaries, and severity signals with deterministic rule-based fallback and live failure reporting.
- 🗣️ **Bilingual Kannada & English (ಕನ್ನಡ):** Localized civic intake for citizens in Mangaluru, Dakshina Kannada, and rural Karnataka.
- 📱 **PWA & Offline Auto-Sync:** Client-side queue with Service Worker asset caching (`civic-action-v2`) for Western Ghats and remote forest sections.
- 🔗 **Spatial Deduplication (150m):** TF-IDF text similarity within 150m radius links duplicates to a primary ticket.
- 📊 **Transparent Additive Priority Scoring (0–100):** Defensible urgency scores with itemized audit reasons.
- 🔥 **Hotspots Hub & Action Briefs:** Zero-latency Hotspots Hub replaces the Leaflet map tab, grouping co-occurring civic failures within 200m via DBSCAN.
- 👮 **Municipal Officer Command Center:** Protected role-based access control with department-specific workflow triage, token expiry, and login throttling.
- 🕒 **Closed-Loop Citizen Tracking & Session Wallet:** Citizens can track tickets without tracking codes via browser session persistence.

---

## ⚠️ Limitations & Honesty Note

1. **No Tile Map:** The Hotspots Hub replaces the map tab entirely. There is no interactive Leaflet tile map to prevent asset loading latency and offline rendering failures.
2. **Officer Authentication & Security:**
   - In-memory bearer tokens have a strict **12-hour expiry** and are lost on container restart.
   - **Login Throttling:** 5 failed login attempts from the same client IP (or `X-Forwarded-For`) within 60 seconds triggers an HTTP 429 lockout for 60 seconds.
   - Demo officer passwords are hardcoded in source by default but can be overridden via `DEMO_OFFICER_PASSWORD` or department-specific environment variables.
   - Wildcard CORS is removed; requests are restricted to same-origin or `localhost:5173`.
   - Security headers are applied to all responses: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, and `Permissions-Policy: geolocation=(self)`.
3. **Report Submission Rate Limiting:** There is currently no rate limiting on the public `POST /api/reports` endpoint.
4. **Public Read Endpoints:** `GET /api/reports` and `GET /api/reports/{id}` are public endpoints and expose internal priority scores and raw complaint text without requiring an officer token. Only mutations (`PATCH /api/reports/{id}/status`, `POST /api/reports/{id}/unlink`, and `POST /api/demo/reset`) enforce officer token authentication.
5. **Ephemeral Cloud Run Storage:** When deployed on Google Cloud Run, SQLite is stored in `/tmp/civic.db`, which resets when instances restart. Deploying with `--min-instances 1 --max-instances 1` keeps data consistent for a single instance.
6. **Offline Photo Limitations:** Photos taken offline are not saved in the offline queue (to avoid browser memory issues); only text, category, and coordinates are queued. Citizens are notified that photos must be re-attached upon sync.
7. **AI Live Verification & Fallback:** The LLM path was verified live against the Groq API on one model (`openai/gpt-oss-20b`). If no key is set or an API call fails, the system automatically falls back to deterministic rule-based triage, logs the failure, and flags `llm_last_error` in `/api/health` and the UI header.
8. **Approximate Location Exclusion:** Reports submitted without GPS coordinates infer approximate ward-centre coordinates from address text and are flagged with `location_approx = 1`. These reports are strictly excluded from duplicate candidate searches and DBSCAN clustering to prevent false hotspot formation.
9. **Upload Validation:** In addition to MIME type headers, uploads are verified against format magic bytes (`\xff\xd8\xff` for JPEG, `\x89PNG` for PNG, `GIF8` for GIF, `RIFF...WEBP` for WebP); mismatches return HTTP 422.
10. **Production Verification:**
    - **Pytest:** 25 passed in 7.17s (14 API integration/security tests + 11 pipeline/AI tests).
    - **Frontend Production Bundle:** `198.79 kB JS` (gzip: 62.86 kB), `30.66 kB CSS` (gzip: 6.16 kB), `0.94 kB HTML`.

---

## ☁️ Deploy to Google Cloud Run

The application is containerized with a 2-stage multi-stage Docker build:
1. `node:22-slim`: builds the React Vite PWA bundle.
2. `python:3.11-slim`: installs backend requirements, copies built SPA assets to `/app/frontend/dist` (served directly by FastAPI), sets `/tmp` database paths, and starts Uvicorn.

### Exact Deployment Command
```bash
gcloud run deploy civic-action \
  --source . \
  --region asia-south1 \
  --allow-unauthenticated \
  --min-instances 1 \
  --max-instances 1 \
  --memory 1Gi \
  --set-env-vars GROQ_API_KEY=your_groq_api_key_here,LLM_MODEL=openai/gpt-oss-20b
```

> **Note on Storage Consistency:** Cloud Run containers use an ephemeral in-memory filesystem in `/tmp`. SQLite database data resets whenever the instance restarts. Configuring `--min-instances 1 --max-instances 1` ensures requests are routed to a single container instance, maintaining consistency throughout demo evaluation.
> *(Local verification note: Docker CLI version 29.6.1 is present on the machine, but the local Docker Desktop engine was not running during this session, so local `docker build` was not run).*

---

## 🏗️ System Architecture

```
React (Vite PWA, Service Worker)  --->  FastAPI Backend  --->  pipeline.py  --->  ai.py
  - Report Issue (Auto-GPS / Text)        /api/*               orchestrator       - Groq LLM (openai/gpt-oss-20b)
  - Track Status (Progress Stepper)       SQLite (WAL mode)                       - TF-IDF Deduplication
  - Officer Command Center (Queue, Hotspots, Dash)                                - Additive Priority (0-100)
                                                                                  - DBSCAN Hotspot Clustering
```

---

## 🚀 Quickstart

### 1. One-Command Launcher (Windows PowerShell)
```powershell
.\civic-action\run.ps1
```

### 2. Unix / macOS
```bash
cd civic-action
chmod +x run.sh && ./run.sh
```

### 3. Manual Startup
```powershell
# Backend
cd civic-action/backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn app.main:app --port 8000 --reload

# Frontend
cd ../frontend
npm install
npm run dev
```

Visit **`http://localhost:8000`** in your browser.

---

## 🧪 Testing

The platform includes 25 deterministic integration, security, and pipeline test suites:

```powershell
python -m pytest
```
```
collected 25 items
civic-action\backend\tests\test_api.py ..............                    [ 56%]
civic-action\backend\tests\test_pipeline.py ...........                  [100%]
======================= 25 passed, 1 warning in 7.17s =======================
```

---

## 👥 Demo Officer Credentials

| Department | Email | PIN / Password | Overridable Env Var |
| :--- | :--- | :--- | :--- |
| **Roads & PWD** | `officer.pwd@mangaluru.gov.in` | `officer123` | `DEMO_OFFICER_PWD_PASSWORD` |
| **Drainage & Sanitation** | `officer.drainage@mangaluru.gov.in` | `officer123` | `DEMO_OFFICER_DRAINAGE_PASSWORD` |
| **Municipal Commissioner** | `officer.admin@mangaluru.gov.in` | `admin123` | `DEMO_OFFICER_ADMIN_PASSWORD` |

*(Pass `DEMO_OFFICER_PASSWORD` to override all accounts simultaneously).*

---

## 📄 License
MIT License. Built for the PromptWars × ASTRA Hackathon.
