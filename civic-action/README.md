# Civic Action: From Complaints to Prioritized, Trackable Action

PromptWars × ASTRA (AI for Civic Impact) prototype. Citizens report a problem; the platform categorizes it, links duplicates, scores and explains its priority, surfaces hotspots for officers, and gives citizens an illuminated timeline they can follow even if they lose their tracking code.

---

## What's New in this Version

1. **⚡ Groq LLM Triage (`Llama-3.3-70b-versatile`):** Rapid extraction with native JSON mode and reliable fallback to deterministic rules.
2. **🗣️ Bilingual Kannada & English (ಕನ್ನಡ):** Localized civic intake for citizens in Mangaluru and coastal Karnataka.
3. **📱 PWA & Offline Auto-Sync:** Zero data loss in Western Ghats and forest sections without mobile connectivity.
4. **📍 Zero-Latency Location:** Removed slow map tile loaders; instant GPS detection with 1-click ward buttons.
5. **👮 Officer Command Center:** Dedicated role-based authentication protecting municipal triage workflows.
6. **📱 "My Reports" Device Wallet:** Solves the lost code problem by preserving citizen ticket history on their device session.

---

## Run it

### Windows PowerShell (Recommended)
```powershell
.\run.ps1            # installs deps, builds UI, serves on http://localhost:8000
```

### Linux / macOS
```bash
./run.sh
```

First start loads 45 synthetic demo reports automatically.

### Optional LLM
Copy `backend/.env.example` to `backend/.env` and set `GROQ_API_KEY`:
```env
GROQ_API_KEY=gsk_your_groq_api_key_here
LLM_MODEL=llama-3.3-70b-versatile
```
Without a key, the app runs entirely on the deterministic multilingual rule-based fallback.

---

## Tests

```powershell
pytest               # 20 tests, deterministic, zero network dependencies
```

---

## Layout

```
civic-action/
  backend/app/
    config.py     # tunables, weights, thresholds, wards
    db.py         # SQLite schema, migrations, connection pool
    ai.py         # pure AI functions: Groq LLM, deduplication, priority, DBSCAN, briefs
    pipeline.py   # DB orchestration around AI functions
    seed.py       # 45 synthetic demo reports for Mangaluru
    main.py       # FastAPI router, officer auth, session recovery, static serving
  backend/tests/
    test_api.py       # API integration & auth test suites
    test_pipeline.py  # AI pipeline, scoring & regional language tests
  frontend/
    public/       # PWA manifest, service worker, icons
    src/
      i18n.js         # Bilingual English & Kannada translation dictionary
      offlineQueue.js # Offline sync queue & device session storage
      api.js          # API client with officer token auth
      App.jsx         # Header, role switcher, navigation, PWA offline banner
      styles.css      # Modern accessible design system
      components/
        LocationInput.jsx     # Zero-latency GPS + text ward picker
        ReportForm.jsx        # Intake form with photo evidence preview
        TrackView.jsx         # Stepper timeline & "My Reports" device wallet
        Queue.jsx             # Officer priority queue with crew assignments
        MapView.jsx           # Hotspots hub & dispatch action briefs
        Dashboard.jsx         # Ward x Category heat matrix & KPI stats
        ResultCard.jsx        # Transparent additive score breakdown
        OfficerLoginModal.jsx # Municipal officer sign-in modal
```
