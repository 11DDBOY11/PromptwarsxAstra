# PromptwarsxAstra — CivicAction Karnataka 🏛️

> **AI for Civic Impact (PromptWars × ASTRA Hackathon Prototype)**  
> Transform unstructured, multilingual citizen complaints into deduplicated, prioritized, and trackable municipal action — even across low-connectivity Western Ghats and forest regions.

---

## 🌟 Key Highlights

- ⚡ **Groq LLM Triage (`Llama-3.3-70b-versatile`):** Rapid extraction of categories, summaries, and severity signals with deterministic rule-based fallback.
- 🗣️ **Bilingual Kannada & English (ಕನ್ನಡ):** Localized civic intake for citizens in Mangaluru, Dakshina Kannada, and rural Karnataka.
- 📱 **PWA & Offline Auto-Sync:** Zero data loss in Western Ghats and remote forest sections without cellular connectivity.
- 🔗 **Spatial Deduplication (150m):** TF-IDF text similarity within 150m radius links duplicates to a primary ticket, eliminating officer alert fatigue.
- 📊 **Transparent Additive Priority Scoring (0–100):** Defensible, explainable urgency scores with itemized audit reasons.
- 🔥 **DBSCAN Incident Hotspots & Action Briefs:** Groups co-occurring civic failures within 200m and drafts multi-crew dispatch plans.
- 👮 **Municipal Officer Command Center:** Protected role-based access control with department-specific workflow triage.
- 🕒 **Closed-Loop Citizen Tracking & Session Wallet:** Citizens never lose their tickets, even without tracking codes, via browser session persistence.

---

## 🏗️ System Architecture

```
React (Vite PWA, Service Worker)  --->  FastAPI Backend  --->  pipeline.py  --->  ai.py
  - Report Issue (Auto-GPS / Text)        /api/*               orchestrator       - Groq LLM (Llama 3.3)
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

The platform includes 20 deterministic integration and pipeline test suites covering authentication, session recovery, Kannada script intake, and priority scoring:

```powershell
pytest
```
```
collected 20 items
backend\tests\test_api.py .........                                      [ 45%]
backend\tests\test_pipeline.py ...........                               [100%]
======================= 20 passed in 5.5s =======================
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
