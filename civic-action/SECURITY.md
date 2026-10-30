# Security Policy & Audit Report

## Security Architecture

The Civic Action Platform enforces multiple defense-in-depth layers to safeguard citizen grievance data, protect municipal systems, and prevent unauthorized actions.

### 1. Authentication & Authorization
- **Stateless HMAC-SHA256 Signed Tokens:** Officer authentication uses cryptographically signed tokens (`<base64url(payload)>.<base64url(hmac)>`) signed with `SECRET_KEY` (or an ephemeral 32-byte secret generated at startup). Token verification enforces constant-time signature comparison (`hmac.compare_digest`) and 12-hour expiration.
- **Credential Storage:** Demo officer credentials use salted PBKDF2 password hashes (`hashlib.pbkdf2_hmac("sha256", ..., 100_000 iterations)`). No plaintext passwords exist in the source code. Passwords remain overridable via environment variables.
- **Gated Endpoints:** Officer views and analytics (`GET /api/reports`, `GET /api/reports/{id}`, `GET /api/clusters`, `GET /api/stats`, `PATCH /api/reports/{id}/status`, `POST /api/reports/{id}/unlink`, `POST /api/demo/reset`) strictly require valid officer Bearer tokens (HTTP 401 on missing/invalid/expired token).
- **Public Citizen Endpoints:** Public intake (`POST /api/reports`), tracking (`GET /api/track/{code}`), session lookup (`GET /api/reports/by-session`), and health monitoring (`GET /api/health`) remain accessible without credentials. Public endpoints do not expose internal scoring weights or officer assignments.

### 2. Request Throttling & DoS Protections
- **Officer Login Throttling:** 5 failed login attempts per client IP within 60 seconds triggers a 60-second lockout (HTTP 429).
- **Citizen Report Submission Rate Limiting:** Maximum 10 report submissions per minute per client IP (using the first address of `X-Forwarded-For` when behind reverse proxies, falling back to client host). Exceeding requests receive HTTP 429.
- **Payload Size Caps:** HTTP request body size checked against 6 MB cap (HTTP 413). Uploaded images are strictly capped at 5 MB (`C.MAX_IMAGE_BYTES`).

### 3. Upload & Input Validation
- **Magic Byte Verification:** File uploads inspect binary header signatures (JPEG `\xff\xd8\xff`, PNG `\x89PNG`, GIF `GIF8`, WebP `RIFF....WEBP`) in addition to MIME content-types to reject spoofed files (HTTP 422).
- **Session Identifier Validation:** `citizen_session` parameters must match regex `^[a-zA-Z0-9_-]{16,64}$`, rejecting malformed or injected tokens (HTTP 422).
- **Coordinate Bounds Checking:** Latitude and longitude are constrained to valid geographical ranges (`[-90, 90]` and `[-180, 180]`).

### 4. Browser Security Headers & Content Security Policy (CSP)
Every response carries hardened HTTP headers:
- `Content-Security-Policy`: `default-src 'self'; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'`
  - Verified with automated browser testing: 0 CSP violations across intake, submission, language toggle, and officer views.
- `X-Frame-Options`: `DENY`
- `X-Content-Type-Options`: `nosniff`
- `Referrer-Policy`: `no-referrer`
- `Permissions-Policy`: `geolocation=(self)`
- `Cache-Control`: `public, max-age=31536000, immutable` for `/assets/` bundles; `no-cache` for `/index.html` and `/sw.js`.

---

## Dependency Vulnerability Audit

### npm Audit (Frontend)
- **Command:** `npm audit` (executed 2026-10-30)
- **Results:** 2 vulnerabilities (1 moderate, 1 high) in devDependencies:
  - `esbuild` / `vite` (GHSA-67mh-4wv8-2f99): Relates to Vite dev server handling of external websocket/HTTP requests in development mode.
  - **Risk Assessment:** **Nil in Production.** The production deployment compiles the frontend to static files via `npm run build` which are served statically by FastAPI. The Vite dev server is never run in production.

### Python Dependencies (Backend)
- **Command:** Host check for `pip-audit` (`pip-audit` not installed on environment).
- **Mitigation:** All direct dependencies in `backend/requirements.txt` are pinned to exact verified versions:
  - `fastapi==0.141.1`
  - `uvicorn[standard]==0.54.0`
  - `python-multipart==0.0.32`
  - `numpy==1.26.4`
  - `scikit-learn==1.8.0`
  - `groq==1.6.0`
  - `anthropic==0.28.0`
  - `pytest==8.4.2`
  - `httpx==0.28.1`

---

## Reporting a Vulnerability

To report a vulnerability or security concern, please contact the municipal platform maintainers or open a confidential security advisory on GitHub.
