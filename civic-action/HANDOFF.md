# Project Engineering Handoff: CivicAction (PromptwarsxAstra)

---

## 1. Overview

CivicAction is an automated civic grievance intake, deduplication, and triage platform built for municipal administration (demonstrated for Mangaluru / Coastal Karnataka). Citizens submit unstructured complaints (with text, GPS/landmark, and optional photos), which the system automatically categorizes, summarizes, scores for urgency, and clusters into incident hotspots. Duplicates within 150m are linked rather than discarded, cascading resolution updates back to citizens. The system features bilingual support (English / Kannada), an installable PWA with offline auto-sync for low-connectivity Western Ghats/forest areas, a device session wallet for lost tracking codes, and a role-gated Municipal Officer Command Center.

### Exact Commands to Run

#### Option A: One-Command Launcher (Windows PowerShell)
```powershell
.\civic-action\run.ps1
```

#### Option B: Manual Commands
```powershell
# 1. Backend Server (from repository root)
cd civic-action/backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# 2. Frontend Development Server (optional, proxies /api to :8000)
cd civic-action/frontend
npm run dev
```

The application is served at **`http://localhost:8000`** (FastAPI serves the pre-built `frontend/dist` directory).

---

## 2. File Map

Total project code: **5,422 lines** across **40 source files** (excluding `node_modules`, `.venv`, `.git`, `dist`, and cached data).

```
civic-action/
├── backend/
│   ├── app/
│   │   ├── __init__.py       (0 lines)   - Package marker.
│   │   ├── config.py         (64 lines)  - Central configuration, thresholds, weights, ward coordinates, and .env loader.
│   │   ├── db.py             (80 lines)  - SQLite schema, migrations (citizen_session), connection pool, and helpers.
│   │   ├── ai.py             (224 lines) - Pure AI functions: Groq LLM calls, Kannada/Hinglish NLP rules, TF-IDF, priority math, DBSCAN.
│   │   ├── pipeline.py       (82 lines)  - Orchestration layer: report creation, deduplication linking, rescoring, and cluster caching.
│   │   ├── seed.py           (75 lines)  - 45 synthetic demo reports (Mangaluru wards, planted duplicates, clusters, near-misses).
│   │   └── main.py           (268 lines) - FastAPI routers: intake, officer auth, session recovery, status workflow, static file serving.
│   ├── tests/
│   │   ├── conftest.py       (6 lines)   - Pytest test environment flags.
│   │   ├── test_api.py       (110 lines) - 9 integration tests covering intake, officer auth, session recovery, tracking, validation.
│   │   └── test_pipeline.py  (75 lines)  - 11 unit tests covering seeding, duplicate linking, scoring, DBSCAN, and Kannada rules.
│   ├── requirements.txt      (9 lines)   - Python dependencies (fastapi, uvicorn, groq, anthropic, scikit-learn, etc.).
│   └── .env.example          (10 lines)  - Environment template with placeholder keys.
├── frontend/
│   ├── public/
│   │   ├── icon.svg          (15 lines)  - Municipal civic shield SVG icon for PWA.
│   │   ├── manifest.json     (16 lines)  - PWA web app manifest.
│   │   └── sw.js             (35 lines)  - Service worker caching app shell for offline functionality.
│   ├── src/
│   │   ├── main.jsx          (6 lines)   - React DOM entry point.
│   │   ├── App.jsx           (306 lines) - Top-level component: header, language switcher, officer auth state, offline banner.
│   │   ├── api.js            (50 lines)  - Fetch client with Bearer token authentication headers.
│   │   ├── utils.js          (41 lines)  - Shared utilities: color maps, ward coordinates, category icons, date formatters.
│   │   ├── i18n.js           (171 lines) - Bilingual English and Kannada (ಕನ್ನಡ) translation dictionary.
│   │   ├── offlineQueue.js   (84 lines)  - LocalStorage offline queue, device session wallet, and auto-sync handler.
│   │   ├── styles.css        (1972 lines)- Complete accessible design system, responsive breakpoints, stepper, and modals.
│   │   └── components/
│   │       ├── LocationInput.jsx     (111 lines) - Zero-latency GPS auto-detection + text ward selection.
│   │       ├── LocationPicker.jsx    (33 lines)  - Legacy Leaflet map picker (retained for reference).
│   │       ├── ReportForm.jsx        (282 lines) - Citizen complaint form with photo preview and offline queueing.
│   │       ├── TrackView.jsx         (251 lines) - 5-step progress stepper and "My Reports on This Device" wallet.
│   │       ├── Queue.jsx             (314 lines) - Officer priority queue, band filtering, search, and crew assignments.
│   │       ├── MapView.jsx           (159 lines) - Fast Hotspots Hub: active DBSCAN cluster bundles and AI action briefs.
│   │       ├── Dashboard.jsx         (210 lines) - Executive KPIs, priority bars, category distribution, Ward x Category heat table.
│   │       ├── ResultCard.jsx        (77 lines)  - Transparent additive priority score breakdown and audit reasons.
│   │       └── OfficerLoginModal.jsx (127 lines) - Officer authentication dialog with 1-click pre-populated demo roles.
│   ├── package.json          (9 lines)   - Frontend dependencies (React 18, Leaflet, Vite).
│   ├── vite.config.js        (7 lines)   - Vite build configuration with React plugin and API proxy.
│   └── index.html            (23 lines)  - HTML root, PWA meta tags, and Service Worker registration.
├── pytest.ini                (3 lines)   - Pytest path configuration.
├── run.ps1                   (34 lines)  - Windows automated launcher script.
├── run.sh                    (9 lines)   - Unix/macOS automated launcher script.
└── README.md                 (65 lines)  - Project documentation.
```

---

## 3. Feature Inventory

| Feature | Status | File and Function | Verification Method |
| :--- | :---: | :--- | :--- |
| **Citizen Capture** | Working | `backend/app/main.py:submit_report` & `frontend/src/components/ReportForm.jsx` | Submitted live via `curl` and frontend; validated 201 response and DB insert. |
| **Categorization** | Working | `backend/app/ai.py:understand` (`understand_llm`, `understand_rules`) | Tested via pytest (`test_categories`, `test_kannada_and_regional_category_rules`). |
| **Summarization** | Working | `backend/app/ai.py:_summary` & `understand_llm` | Verified via live test script: generates concise summary under 20 words. |
| **Duplicate Detection** | Working | `backend/app/pipeline.py:find_duplicate` & `backend/app/ai.py:similarities` | Verified via `test_duplicate_groups_link_to_one_primary` (Kadri & Kankanady planted sets). |
| **Priority Scoring** | Working | `backend/app/ai.py:priority` | Verified via `test_priority_reasons_sum_to_score` (math verified: 20+10+10+6+7+2 = 55). |
| **Hotspot Clustering** | Working | `backend/app/ai.py:find_clusters` & `backend/app/pipeline.py:refresh` | Verified via `test_hotspot_found_with_mixed_categories` (Bunder cluster of 6 issues found). |
| **Action Briefs** | Working | `backend/app/ai.py:make_brief`, `template_brief` | Verified in database output and `GET /api/clusters`. |
| **Map / Hotspots Hub**| Working | `frontend/src/components/MapView.jsx` & `GET /api/clusters` | Verified in browser UI; renders active cluster cards with zero tile latency. |
| **Dashboard** | Working | `frontend/src/components/Dashboard.jsx` & `backend/app/main.py:stats` | Verified via `test_reveal_endpoints` (`GET /api/stats` returns KPIs and matrix). |
| **Officer Queue** | Working | `frontend/src/components/Queue.jsx` & `backend/app/main.py:list_reports` | Verified via UI and `GET /api/reports?include_duplicates=false`. |
| **Citizen Tracking** | Working | `frontend/src/components/TrackView.jsx` & `backend/app/main.py:track` | Verified via `test_full_journey`; internal priority scores hidden from citizens. |
| **Officer Auth** | Working | `backend/app/main.py:_verify_officer`, `officer_login`, `officer_me` | Verified via `test_officer_authentication` (valid token succeeds; bad token returns 401). |
| **Kannada / i18n** | Working | `frontend/src/i18n.js` & `backend/app/ai.py:SYN`, `CATEGORY_RULES` | Verified via `test_kannada_language_complaint_intake` and `test_kannada_and_regional_category_rules`. |
| **Offline / PWA** | Working | `frontend/public/sw.js` & `frontend/src/offlineQueue.js` | Verified PWA manifest registration and offline queue sync simulation. |
| **Citizen Session History** | Working | `frontend/src/offlineQueue.js` & `backend/app/main.py:get_reports_by_session` | Verified via `test_citizen_session_tracking_and_recovery`. |
| **Ward Inference from Address** | Working | `backend/app/main.py:submit_report` (lines 104-113) | Verified via `test_address_text_infers_ward_coordinates` (Kadri address -> `12.8885, 74.8530`). |

---

## 4. AI Details

### Live API Status & Models
- **API Client:** Groq Python SDK (`groq.Groq`) with fallback support for Anthropic (`anthropic.Anthropic`).
- **Configured Model in code:** `LLM_MODEL = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")` in `config.py`.
- **Live Call Verification:** Verified against live Groq API using user-provided key.
  - *Observation:* The account associated with this key returned `404 - model not found` for `llama-3.3-70b-versatile`.
  - *Observation:* Testing against available models on this key confirmed live execution with `openai/gpt-oss-20b` (`ai_mode: "llm"`).
  - *Fallback Behavior:* When no API key is set, or when the model name errors (404/timeout), `ai._llm_json` catches the exception and returns `None`. The system silently falls back to deterministic rule extraction (`ai_mode: "rules"`).

### Duplicate Similarity Method & Thresholds
- **Pre-filtering:** Candidates are strictly filtered to open (unresolved), primary (`duplicate_of IS NULL`) tickets with the **exact same category** within **150 meters** (`DUP_RADIUS_M = 150`, computed via Haversine).
- **Text Similarity:**
  - Default embedder: **TF-IDF with sublinear term frequency** (`TfidfVectorizer(ngram_range=(1, 2), stop_words="english", sublinear_tf=True)`).
  - Similarity metric: **Cosine similarity** (`(m[1:] @ m[0].T)`).
  - Threshold: **`0.18`** (`DUP_MIN_SIM["tfidf"] = 0.18`).
  - Optional sentence-transformers embedder: `all-MiniLM-L6-v2` with cosine threshold **`0.78`** (`EMBEDDER=st`).

### Priority Scoring Formula & Weights
The numerical priority score ($0\text{--}100$) is strictly additive; the LLM supplies signals, never the number.

$$\text{Score} = \text{Safety} + \text{People} + \text{Blocks Access} + \text{Worsening} + \text{Duplicates} + \text{Hotspot} + \text{Age}$$

- **Safety Risk (`safety_risk` 0..3):**
  - Level 0: `+0`
  - Level 1: `+8`
  - Level 2: `+20`
  - Level 3: `+35` *(If Level 3, the total score is clamped to a floor of at least 70)*.
- **People Affected (`people_affected` 0..3):**
  - Level 0: `+0`
  - Level 1: `+4`
  - Level 2: `+10`
  - Level 3: `+20` (near schools, hospitals, transit hubs, markets).
- **Blocks Road or Access (`blocks_access`):** `+10`
- **Condition Getting Worse (`worsening`):** `+8`
- **Linked Duplicates:** `+3` per linked duplicate report (capped at 5 reports = maximum `+15`).
- **Inside Hotspot (`in_cluster`):** `+7`
- **Age Penalty:** `+1` per day past 3 grace days (`AGE_GRACE_DAYS = 3`), capped at 10 days (`AGE_CAP = 10`, max `+10`).
- **Priority Bands:**
  - **Critical:** $\ge 70$
  - **High:** $\ge 45$
  - **Medium:** $\ge 20$
  - **Low:** $< 20$

### Clustering Parameters
- **Algorithm:** DBSCAN with haversine metric on radian coordinates (`eps = 200 / 6371000.0`, algorithm `ball_tree`).
- **Inputs:** Open, non-duplicate reports (`duplicate_of IS NULL AND status != 'Resolved'`).
- **Thresholds:** `CLUSTER_EPS_M = 200` meters, `CLUSTER_MIN = 3` reports.
- **Caching:** Action briefs are memoized by a sorted CSV string of member report IDs (`member_key`). Unchanged clusters reuse their cached brief without re-calling the LLM.

---

## 5. API Reference

| Method | Path | Auth Required | Request Body / Query Params | Response Summary |
| :--- | :--- | :---: | :--- | :--- |
| `POST` | `/api/auth/officer-login` | No | JSON: `{"email": str, "password": str}` | `{"token": str, "officer": {...}}` |
| `GET` | `/api/auth/officer-me` | Yes (`Bearer <token>`) | Headers: `Authorization: Bearer <token>` | `{"ok": true, "officer": {...}}` |
| `POST` | `/api/reports` | No | Multipart Form: `text: str, lat?: float, lng?: float, address?: str, category?: str, citizen_session?: str, image?: file` | Full report dictionary with tracking code, priority, and signals. |
| `GET` | `/api/reports` | No | Query: `status?: str, include_duplicates?: bool = false` | List of report objects with `linked_count`. |
| `GET` | `/api/reports/{id}` | No | Path: `id: int` | Detailed report with `events`, `linked`, and `cluster`. |
| `PATCH`| `/api/reports/{id}/status` | Yes (`Bearer <token>`) | JSON: `{"status": str, "assignee"?: str, "note"?: str}` | Updated report object (cascades to all duplicates). |
| `POST` | `/api/reports/{id}/unlink` | Yes (`Bearer <token>`) | Path: `id: int` | Updated report object with `duplicate_of: null`. |
| `GET` | `/api/reports/by-session` | No | Query: `session_id: str` | Array of reports submitted by that device session. |
| `GET` | `/api/track/{code}` | No | Path: `code: str` | Public tracking view (status, timeline, events; no internal score). |
| `GET` | `/api/clusters` | No | None | List of active DBSCAN cluster objects with action briefs and members. |
| `GET` | `/api/stats` | No | None | Municipal KPI statistics, category counts, ward matrix, and 10-day volume. |
| `GET` | `/api/health` | No | None | Health status, report count, active AI mode, embedder, and category list. |
| `POST` | `/api/demo/reset` | No (gated by env) | None (gated by `ALLOW_DEMO_RESET != "0"`) | `{"seeded": 45}` |

---

## 6. Data Model

Database: SQLite (`backend/data/civic.db`) with WAL mode enabled.

### Table: `reports`
| Column | Type | Constraints / Description |
| :--- | :--- | :--- |
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT |
| `tracking_code` | TEXT | UNIQUE NOT NULL (Format: `CIV-XXXXXX`) |
| `text` | TEXT | NOT NULL (Complaint description) |
| `image_path` | TEXT | Uploaded file name in `uploads/` |
| `user_category` | TEXT | Optional user-selected category guess |
| `lat` | REAL | NOT NULL (-90 to +90) |
| `lng` | REAL | NOT NULL (-180 to +180) |
| `address` | TEXT | Landmark / street string |
| `ward` | TEXT | Inferred ward name |
| `created_at` | TEXT | ISO-8601 UTC timestamp |
| `status` | TEXT | NOT NULL DEFAULT `'Submitted'` |
| `assignee` | TEXT | Assigned crew or officer name |
| `category` | TEXT | AI/rule assigned category |
| `summary` | TEXT | Short summary (max 20 words) |
| `signals` | TEXT | JSON object of extracted signals |
| `ai_mode` | TEXT | `'llm'` or `'rules'` |
| `priority_score`| INTEGER | DEFAULT 0 (0-100 scale) |
| `priority_band` | TEXT | DEFAULT `'Low'` (Critical / High / Medium / Low) |
| `reasons` | TEXT | JSON array of human-readable score additions |
| `duplicate_of` | INTEGER | REFERENCES `reports(id)` |
| `duplicate_score`| REAL | Cosine similarity score |
| `cluster_id` | INTEGER | REFERENCES `clusters(id)` |
| `citizen_session`| TEXT | Browser device session identifier |

**Indexes on `reports`:**
- `idx_reports_status` on `reports(status)`
- `idx_reports_dup` on `reports(duplicate_of)`
- `idx_reports_session` on `reports(citizen_session)`

### Table: `clusters`
| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT |
| `centroid_lat` | REAL | Mean latitude of cluster members |
| `centroid_lng` | REAL | Mean longitude of cluster members |
| `radius_m` | REAL | Bounding radius in meters |
| `report_count` | INTEGER | Number of clustered primary reports |
| `categories` | TEXT | JSON map of category to count |
| `ward` | TEXT | Nearest ward name |
| `member_key` | TEXT | Sorted comma-separated list of member IDs |
| `brief` | TEXT | 3-sentence action dispatch brief |
| `ai_mode` | TEXT | `'llm'` or `'template'` |

### Table: `status_events`
| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT |
| `report_id` | INTEGER | NOT NULL REFERENCES `reports(id)` |
| `status` | TEXT | Status transition name |
| `note` | TEXT | Officer update note |
| `assignee` | TEXT | Crew assigned at this step |
| `at` | TEXT | ISO-8601 UTC timestamp |

**Indexes on `status_events`:**
- `idx_events_report` on `status_events(report_id)`

---

## 7. Security

### Officer Authentication Details
- **Token Generation:** Generated via `f"mcc-{uuid.uuid4().hex}"` upon valid credentials.
- **Token Storage:** Stored in an in-memory dictionary (`OFFICER_TOKENS = {}`) in `backend/app/main.py`.
- **Token Expiry:** **None.** Tokens persist indefinitely in memory until the FastAPI process restarts.
- **Client Storage:** Stored in browser `localStorage` under `civic_officer_token` and sent via `Authorization: Bearer <token>`.
- **Credentials Source:** Hardcoded in `DEMO_OFFICERS` in `backend/app/main.py`.

### Hardcoded Demo Credentials Committed in Repository
```python
1. "officer.pwd@mangaluru.gov.in"      / "officer123"  (Road Infrastructure - PWD)
2. "officer.drainage@mangaluru.gov.in" / "officer123"  (Stormwater Drainage & Sanitation)
3. "officer.admin@mangaluru.gov.in"    / "admin123"    (Mangaluru City Corporation Administration)
```

### Rendering & XSS Audit
- React components render text via standard JSX expressions (`{r.text}`, `{r.summary}`, `{r.address}`), which automatically escape HTML entities.
- Zero instances of `dangerouslySetInnerHTML` exist in the frontend codebase.
- The legacy `LocationPicker.jsx` containing `bindPopup` with raw template strings is unreferenced in the active application; all active views use `LocationInput.jsx`.

### Upload Validation
- MIME type validated against `IMAGE_EXT` (`image/jpeg`, `image/png`, `image/webp`, `image/gif`).
- Size capped at 5 MB (`len(data) > 5 * 1024 * 1024` returns HTTP 413).
- Saved with random UUID hex filenames (`f"{uuid.uuid4().hex}{ext}"`).
- *Weakness:* Content is validated strictly from the `Content-Type` header; file magic bytes are not verified.

### CORS Settings
- Permissive wildcard configuration in `backend/app/main.py`:
  ```python
  app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
  ```

### Known Security Weaknesses
1. In-memory auth tokens are lost on server restart and never expire.
2. Hardcoded plaintext passwords in `main.py`.
3. No rate limiting on public `/api/reports` or `/api/auth/officer-login`.
4. Wildcard CORS allows requests from any origin.
5. `POST /api/demo/reset` can wipe the database if `ALLOW_DEMO_RESET` is not explicitly set to `"0"`.

---

## 8. Tests

Ran full test suite command: `python -m pytest`
**Result: 21 passed, 1 warning in 6.58 seconds.**

```
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-8.4.2, pluggy-1.6.0
rootdir: E:\prompt_wars\Astra\PromptwarsxAstra
configfile: pytest.ini
testpaths: civic-action/backend/tests
collected 21 items

civic-action\backend\tests\test_api.py ..........                         [ 47%]
civic-action\backend\tests\test_pipeline.py ...........                  [100%]
======================== 21 passed, 1 warning in 6.58s ========================
```

### Test Inventory
1. `test_seed_size`: Confirms database seeds exactly 45 reports.
2. `test_categories`: Verifies keyword category classification and "other" fallback.
3. `test_duplicate_groups_link_to_one_primary`: Checks that Kadri potholes (4) and Kankanady bins (3) collapse into single primary tickets.
4. `test_near_misses_are_not_merged`: Confirms issues > 150m or with different categories are not falsely linked.
5. `test_urgent_items_are_critical_and_explained`: Verifies planted critical hazards receive scores $\ge 70$.
6. `test_priority_reasons_sum_to_score`: Verifies exact arithmetic tally of priority reasons.
7. `test_hotspot_found_with_mixed_categories`: Confirms DBSCAN detects the Bunder cluster (6 reports across $\ge 2$ categories).
8. `test_new_report_joins_hotspot_and_links_duplicate`: Tests lifecycle of a newly submitted incident joining an existing cluster.
9. `test_llm_garbage_output_falls_back`: Verifies invalid LLM JSON falls back to rule engine.
10. `test_llm_valid_output_is_validated_and_clamped`: Tests signal clamping (0..3) on valid LLM responses.
11. `test_kannada_and_regional_category_rules`: Verifies Kannada script and transliterated terms match correct categories.
12. `test_health_and_seeded`: Validates `/api/health` status and 45 reports baseline.
13. `test_full_journey`: Tests report submission, officer assignment, status update, and public citizen tracking view.
14. `test_duplicates_follow_primary_and_can_be_unlinked`: Verifies status cascade to duplicates and officer unlink operation.
15. `test_validation`: Verifies HTTP 422 on invalid coordinates, short text, or invalid MIME types.
16. `test_reveal_endpoints`: Verifies `/api/stats` and `/api/clusters` output structures.
17. `test_officer_authentication`: Tests invalid credentials (401), valid login (200), token decode, token rejection, and unauthenticated protection on guarded endpoints.
18. `test_citizen_session_tracking_and_recovery`: Verifies reports submitted with `citizen_session` are retrievable via `/api/reports/by-session`.
19. `test_address_text_infers_ward_coordinates`: Verifies text address without GPS coordinates infers ward centroid coordinates.
20. `test_kannada_language_complaint_intake`: Verifies UTF-8 intake of Kannada script complaint.
21. `test_approx_location_reports_never_cluster_or_duplicate`: Verifies address-only reports with approximate locations are excluded from duplicate matching and DBSCAN hotspot clustering.

---

## 9. Frontend

### Production Build Metrics
Command: `npm run build` inside `civic-action/frontend`
- `dist/index.html`: **0.94 kB** (gzip: 0.57 kB)
- `dist/assets/index-BOsUDnqV.css`: **30.66 kB** (gzip: 6.16 kB)
- `dist/assets/index-B2jLcKXE.js`: **198.79 kB** (gzip: 62.86 kB)
- Build time: **1.84 seconds**

### Dependencies (`package.json`)
- `react`: `^18.3.1`
- `react-dom`: `^18.3.1`
*(Note: Leaflet and its CSS were removed entirely in favor of the lightweight Hotspots Hub)*
- `react-dom`: `^18.3.1`
- `leaflet`: `^1.9.4`
- `@vitejs/plugin-react`: `^4.3.4`
- `vite`: `^5.4.11`

### Offline Capabilities & Syncing
- **PWA Caching:** Service Worker (`sw.js`) precaches `/`, `/index.html`, `/manifest.json`, and `/icon.svg`. The application loads while offline.
- **Offline Storage:** When offline (`!navigator.onLine`), `ReportForm.jsx` stores grievances into `localStorage` under `civic_offline_queue`.
- **Sync Trigger:** When connectivity is restored, `window.addEventListener("online")` invokes `syncOfflineQueue()`, which reads the queue, submits multipart forms to `POST /api/reports`, updates the device wallet (`civic_citizen_reports`), and clears the queue.

---

## 10. Seed Data

Total seeded reports: **45** (defined in `backend/app/seed.py`).

- **Planted Cluster (6 reports):** Bunder Road within 100m (drain blockage, knee-deep flood, potholes, house flooding, broken slab, road washed away). Forms Hotspot #1 in Bunder Ward.
- **Planted Pothole Duplicates (4 reports):** Kadri Temple Road near signal (`12.8885, 74.8530`). 1 primary + 3 duplicates (one in Hinglish: *"deep gadda"*).
- **Planted Waste Bin Duplicates (3 reports):** Kankanady market gate (`12.8640, 74.8590`). 1 primary + 2 duplicates (*"kachra bin full"*).
- **Planted Urgent Hazards (3 reports):**
  - Open manhole at Bejai school gate (Safety Risk 3 -> Critical band, score $\ge 70$).
  - Live electric wire sparking on Attavar road (Safety Risk 3 -> Critical band, score $\ge 70$).
  - Fallen tree blocking Falnir road (Safety Risk 3 -> Critical band, score $\ge 70$).
- **Planted Near-Misses (3 reports):** Same text as duplicates but located 2 km away (Bejai main road, Attavar) or different category (Streetlight at Bunder junction). Do NOT link.
- **Routine Background Reports (26 reports):** Distributed on a sparse grid across Mangaluru localities (Hampankatta, Lalbagh, Pumpwell, etc.) with ages ranging from 0 to 9 days.

---

## 11. Known Bugs & Discrepancies

1. **Groq Model Name Discrepancy:** `config.py` defaults to `llama-3.3-70b-versatile`. On the current API key, this returns `404 model not found`. The code silently falls back to `rules`. Setting `LLM_MODEL=openai/gpt-oss-20b` in `.env` activates the live LLM path.
2. **README Map Tab Reference:** The original README describes an interactive Leaflet map tab. The active UI replaces this with the zero-latency **Hotspots Hub** (`MapView.jsx`) to avoid external tile latency.
3. **One-Way Deduplication Linking:** Duplicate detection compares incoming reports only against existing primaries. If Report A arrives before Report B, B links to A. If A is later resolved, B remains subordinate until manually unlinked.
4. **Synthetic Coordinates for Wards:** Wards are approximated via 8 centroid coordinates (`C.WARDS`). Distance-to-centroid determines ward assignment; true administrative GIS polygons are not implemented.

---

## 12. Ten Riskiest Places in the Code

1. **`backend/app/main.py:35-49` (`_verify_officer`):** Pytest bypass logic checks `"PYTEST_CURRENT_TEST" in os.environ`. If an environment variable is leaked or misconfigured in production, auth checks could be bypassed.
2. **`backend/app/ai.py:88-124` (`_llm_json`):** Catches all exceptions with bare `except Exception: return None`. Provider rate-limits (429), model 404s, or bad JSON fail silently without server log traces.
3. **`backend/app/pipeline.py:13-25` (`find_duplicate`):** Re-instantiates and re-fits `TfidfVectorizer` over the entire `reports` table on every incoming report. Computational cost will scale quadratically with volume.
4. **`backend/app/pipeline.py:41-66` (`refresh`):** Completely deletes all rows from `clusters` and recalculates DBSCAN across all unresolved reports on every report submission or status update.
5. **`backend/app/main.py:230-247` (`update_status`):** Cascades status updates to duplicates via sequential SQLite updates inside a loop followed by a full `pipeline.refresh()`.
6. **`backend/app/main.py:104-113` (`submit_report` address inference):** Matches ward names using case-insensitive substring search on address. If no ward matches, silently defaults to Mangaluru center `(12.8700, 74.8500)`.
7. **`frontend/src/offlineQueue.js:46-77` (`syncOfflineQueue`):** Iterates over local queue items. If an item fails validation (e.g. text under 5 characters), it remains in `localStorage` and retries on every online event.
8. **`frontend/src/api.js:9-16` (`getAuthHeaders`):** Reads officer token directly from `localStorage`. Does not check client-side expiry; invalid tokens cause 401 errors until the user manually logs out.
9. **`backend/app/config.py:7-17` (`.env` loader):** Custom file parser uses simple `split("=", 1)`. Does not handle multi-line strings, variable expansion, or escaped quotation marks.
10. **`backend/app/main.py:280-285` (`demo_reset`):** Unauthenticated POST endpoint that deletes and re-seeds all database records. Depends entirely on `ALLOW_DEMO_RESET` env var.

---

## 13. What Would Break in a Live Demo

- **Default Groq Key with Default Model:** If booted with `LLM_MODEL=llama-3.3-70b-versatile` without verifying key permissions, the app will silently run on rule fallbacks. Model must be explicitly set to an accessible model (e.g. `openai/gpt-oss-20b`).
- **Server Restart Clears Officer Logins:** Because `OFFICER_TOKENS` is stored in an in-memory dictionary, restarting the backend server while an officer is presenting will cause their next action to fail with `401 Unauthorized` until they re-login.
- **Database File Locking on Windows:** Running multiple uvicorn workers or parallel test suites while the server is active can trigger `sqlite3.OperationalError: database is locked` on Windows.
- **Offline Report Photos:** Photos captured while offline in Ghat sections are lost if the citizen refreshes the browser before reconnecting, because binary files are not serialized to `localStorage` (only text and coordinates are preserved in the offline queue).
- **Out-of-Town Coordinates:** Submitting coordinates outside Mangaluru (e.g. Bengaluru or Delhi) will forcibly assign the issue to the nearest Mangaluru ward centroid without warning.

