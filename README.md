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
- 👮 **Municipal Officer Command Center:** Protected role-based access control with department-specific workflow triage.
- 🕒 **Closed-Loop Citizen Tracking & Session Wallet:** Citizens can track tickets without tracking codes via browser session persistence.

---

## ⚠️ Limitations & Honesty Note

1. **No Tile Map:** The Hotspots Hub replaces the map tab entirely. There is no interactive Leaflet tile map to prevent asset loading latency and offline rendering failures.
2. **Demo-Grade Officer Auth:** Officer authentication is demo-grade. It uses three hardcoded accounts, in-memory tokens (`mcc-...`) that never expire and are lost on server restart, no rate limiting, and wildcard CORS (`allow_origins=["*"]`).
3. **Public Report APIs:** `GET /api/reports` and `GET /api/reports/{id}` are public endpoints and expose internal priority scores and raw complaint text without requiring an officer token. Only mutations (`PATCH /api/reports/{id}/status`, `POST /api/reports/{id}/unlink`, and `POST /api/demo/reset`) enforce officer token authentication.
4. **Offline Photo Limitations:** Photos taken offline are not saved in the offline queue (to avoid browser memory issues); only text, category, and coordinates are queued. Citizens are notified that photos must be re-attached upon sync.
5. **AI Live Verification & Fallback:** The LLM path was verified live against the Groq API on one model (`openai/gpt-oss-20b`). If no key is set or an API call fails, the system automatically falls back to deterministic rule-based triage, logs the failure, and flags `llm_last_error` in `/api/health` and the UI header.
6. **Approximate Location Exclusion:** Reports submitted without GPS coordinates infer approximate ward-centre coordinates from address text and are flagged with `location_approx = 1`. These reports are strictly excluded from duplicate candidate searches and DBSCAN clustering to prevent false hotspot formation.
7. **Production Verification:**
   - **Pytest:** 21 passed in 5.98s (10 API integration tests + 11 pipeline/AI tests).
   - **Frontend Production Bundle:** `198.79 kB JS` (gzip: 62.86 kB), `30.66 kB CSS` (gzip: 6.16 kB), `0.94 kB HTML`.

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

The platform includes 21 deterministic integration and pipeline test suites covering authentication, session recovery, Kannada script intake, approximate location guards, and priority scoring:

```powershell
python -m pytest
```
```
collected 21 items
civic-action\backend\tests\test_api.py ..........                         [ 47%]
civic-action\backend\tests\test_pipeline.py ...........                  [100%]
======================= 21 passed in 5.98s =======================
```

---

## 👥 Demo Officer Credentials

| Department | Email | PIN / Password |
| :--- | :--- | :--- |
| **Roads & PWD** | `officer.pwd@mangaluru.gov.in` | `officer123` |
| **Drainage & Sanitation** | `officer.drainage@mangaluru.gov.in` | `officer123` |
| **Municipal Commissioner** | `officer.admin@mangaluru.gov.in` | `admin123` |

---

## 📄 License
MIT License. Built for the PromptWars × ASTRA Hackathon.
