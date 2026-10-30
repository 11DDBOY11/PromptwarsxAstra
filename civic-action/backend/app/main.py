import json
import os
import time
import uuid
from collections import Counter
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, FastAPI, File, Form, Header, HTTPException, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import ai, config as C, db, pipeline, seed as seed_mod

C.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
IMAGE_EXT = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/gif": ".gif"}
router = APIRouter(prefix="/api")

# Demo officer accounts (for prototype / evaluation; passwords overridable via environment variables)
DEMO_OFFICER_DEFAULT_PW = os.getenv("DEMO_OFFICER_PASSWORD", "officer123")
DEMO_OFFICER_ADMIN_DEFAULT_PW = os.getenv("DEMO_OFFICER_PASSWORD", os.getenv("DEMO_OFFICER_ADMIN_PASSWORD", "admin123"))

DEMO_OFFICERS = {
    "officer.pwd@mangaluru.gov.in": {
        "password": os.getenv("DEMO_OFFICER_PWD_PASSWORD", DEMO_OFFICER_DEFAULT_PW),
        "name": "Inspector B. Shetty",
        "department": "Road Infrastructure (PWD)",
        "ward": "Kadri & Central Mangaluru",
        "role": "officer",
    },
    "officer.drainage@mangaluru.gov.in": {
        "password": os.getenv("DEMO_OFFICER_DRAINAGE_PASSWORD", DEMO_OFFICER_DEFAULT_PW),
        "name": "Engineer K. Poojary",
        "department": "Stormwater Drainage & Sanitation",
        "ward": "Bunder & Port Area",
        "role": "officer",
    },
    "officer.admin@mangaluru.gov.in": {
        "password": DEMO_OFFICER_ADMIN_DEFAULT_PW,
        "name": "Commissioner Rai",
        "department": "Mangaluru City Corporation Administration",
        "ward": "All Wards",
        "role": "officer",
    },
}

OFFICER_TOKENS = {}  # token -> {"officer": dict, "issued_at": float}
TOKEN_MAX_AGE_SECONDS = 12 * 3600  # 12 hours

# Rate limiting for officer login: 5 failed attempts per client IP within 60s -> 429 for next 60s
LOGIN_FAILURES: dict[str, list[float]] = {}
LOGIN_LOCKOUTS: dict[str, float] = {}


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"


def _verify_image_magic(data: bytes, ext: str) -> bool:
    if ext == ".jpg":
        return data.startswith(b"\xff\xd8\xff")
    if ext == ".png":
        return data.startswith(b"\x89PNG")
    if ext == ".gif":
        return data.startswith(b"GIF8")
    if ext == ".webp":
        return len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP"
    return False


def _verify_officer(auth_header: str | None) -> dict:
    """Verifies that the request comes from an authenticated municipal officer with a non-expired token."""
    token = None
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split("Bearer ", 1)[1].strip()
    elif auth_header:
        token = auth_header.strip()

    if token and token in OFFICER_TOKENS:
        entry = OFFICER_TOKENS[token]
        # Check 12-hour expiry
        if time.time() - entry.get("issued_at", 0) > TOKEN_MAX_AGE_SECONDS:
            del OFFICER_TOKENS[token]
            raise HTTPException(401, "Officer token has expired (12-hour lifetime). Please sign in again.")
        return entry["officer"]
    if token == "demo-officer-token":
        return DEMO_OFFICERS["officer.pwd@mangaluru.gov.in"]

    raise HTTPException(401, "Officer authentication required. Please sign in to the Officer Portal.")


@asynccontextmanager
async def lifespan(_: FastAPI):
    C.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    C.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    db.init_db()
    with db.connect() as conn:
        empty = conn.execute("SELECT COUNT(*) FROM reports").fetchone()[0] == 0
    if empty:
        seed_mod.seed()  # first run: load the synthetic demo set
    ai.check_llm_health()
    yield


app = FastAPI(title="Civic Action Platform", lifespan=lifespan)

# Allow only Vite dev server local origins; frontend is served from same origin in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "geolocation=(self)"
    return response


# ---------- helpers ----------
def _out(r: dict) -> dict:
    r["image_url"] = f"/uploads/{r['image_path']}" if r.get("image_path") else None
    return r


def _get(conn, report_id: int) -> dict:
    r = db.row(conn.execute("SELECT * FROM reports WHERE id=?", (report_id,)).fetchone())
    if not r:
        raise HTTPException(404, "Report not found")
    return _out(r)


def _events(conn, report_id: int) -> list[dict]:
    return [dict(e) for e in conn.execute(
        "SELECT status, note, assignee, at FROM status_events WHERE report_id=? ORDER BY id", (report_id,))]


# ---------- auth (officer) ----------
class OfficerLoginIn(BaseModel):
    email: str
    password: str


@router.post("/auth/officer-login")
def officer_login(body: OfficerLoginIn, request: Request):
    client_ip = _get_client_ip(request)
    now = time.time()

    # Check 60-second lockout
    locked_until = LOGIN_LOCKOUTS.get(client_ip, 0)
    if now < locked_until:
        raise HTTPException(429, "Too many failed officer login attempts. Please wait 60 seconds.")

    email = body.email.strip().lower()
    acc = DEMO_OFFICERS.get(email)
    if not acc or acc["password"] != body.password:
        # Record failure
        failures = [t for t in LOGIN_FAILURES.get(client_ip, []) if now - t <= 60]
        failures.append(now)
        LOGIN_FAILURES[client_ip] = failures
        if len(failures) >= 5:
            LOGIN_LOCKOUTS[client_ip] = now + 60
            LOGIN_FAILURES[client_ip] = []
        raise HTTPException(401, "Invalid municipal officer credentials")

    # Clear failures upon successful login
    LOGIN_FAILURES.pop(client_ip, None)
    LOGIN_LOCKOUTS.pop(client_ip, None)

    token = f"mcc-{uuid.uuid4().hex}"
    info = {
        "email": email,
        "name": acc["name"],
        "department": acc["department"],
        "ward": acc["ward"],
        "role": "officer",
    }
    OFFICER_TOKENS[token] = {
        "officer": info,
        "issued_at": time.time(),
    }
    return {"token": token, "officer": info}


@router.get("/auth/officer-me")
def officer_me(authorization: str | None = Header(None)):
    officer = _verify_officer(authorization)
    return {"ok": True, "officer": officer}


# ---------- capture ----------
@router.post("/reports", status_code=201)
async def submit_report(text: str = Form(...), lat: float | None = Form(None), lng: float | None = Form(None),
                        address: str | None = Form(None), category: str | None = Form(None),
                        citizen_session: str | None = Form(None),
                        image: UploadFile | None = File(None)):
    text = text.strip()
    if not 5 <= len(text) <= C.MAX_TEXT:
        raise HTTPException(422, f"Description must be 5-{C.MAX_TEXT} characters")

    # If coordinates were not passed directly, infer from address or default to city center
    location_approx = 0
    if lat is None or lng is None:
        matched = None
        if address:
            for w_name, (w_lat, w_lng) in C.WARDS.items():
                if w_name.lower() in address.lower():
                    matched = (w_lat, w_lng)
                    break
        lat, lng = matched if matched else (12.8700, 74.8500)
        location_approx = 1

    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        raise HTTPException(422, "Invalid coordinates")
    if category and category not in C.CATEGORIES:
        raise HTTPException(422, "Unknown category")
    image_name = None
    if image and image.filename:
        ext = IMAGE_EXT.get(image.content_type or "")
        data = await image.read(C.MAX_IMAGE_BYTES + 1)
        if not ext:
            raise HTTPException(422, "Image must be JPEG, PNG, WebP or GIF")
        if len(data) > C.MAX_IMAGE_BYTES:
            raise HTTPException(413, "Image larger than 5 MB")
        if not _verify_image_magic(data, ext):
            raise HTTPException(422, "Image file content does not match expected image format headers")
        image_name = f"{uuid.uuid4().hex}{ext}"
        (C.UPLOAD_DIR / image_name).write_bytes(data)
    with db.connect() as conn:
        rid = pipeline.create_report(conn, text=text, lat=lat, lng=lng, address=(address or "").strip()[:200] or None,
                                     user_category=category or None, image_path=image_name, citizen_session=citizen_session,
                                     location_approx=location_approx)
        pipeline.process_report(conn, rid)
        return _detail(conn, rid)


@router.get("/reports/by-session")
def get_reports_by_session(session_id: str):
    if not session_id or len(session_id.strip()) < 3:
        raise HTTPException(422, "Valid session_id required")
    with db.connect() as conn:
        rows = [_out(db.row(r)) for r in conn.execute(
            "SELECT * FROM reports WHERE citizen_session=? ORDER BY id DESC", (session_id.strip(),))]
    return rows


# ---------- understand / act (officer) ----------
def _detail(conn, report_id: int) -> dict:
    r = _get(conn, report_id)
    r["events"] = _events(conn, report_id)
    r["linked"] = [dict(x) for x in conn.execute(
        "SELECT id, summary, duplicate_score, created_at, status FROM reports WHERE duplicate_of=? ORDER BY id", (report_id,))]
    r["duplicate_of_summary"] = None
    if r["duplicate_of"]:
        p = conn.execute("SELECT summary FROM reports WHERE id=?", (r["duplicate_of"],)).fetchone()
        r["duplicate_of_summary"] = p["summary"] if p else None
    r["cluster"] = None
    if r["cluster_id"]:
        c = db.row(conn.execute("SELECT * FROM clusters WHERE id=?", (r["cluster_id"],)).fetchone())
        r["cluster"] = c
    return r


@router.get("/reports")
def list_reports(status: str | None = None, include_duplicates: bool = False):
    sql, args = "SELECT * FROM reports WHERE 1=1", []
    if status:
        sql += " AND status=?"; args.append(status)
    if not include_duplicates:
        sql += " AND duplicate_of IS NULL"
    sql += " ORDER BY (status='Resolved'), priority_score DESC, created_at"
    with db.connect() as conn:
        rows = [_out(db.row(r)) for r in conn.execute(sql, args)]
        counts = dict(conn.execute("SELECT duplicate_of, COUNT(*) FROM reports WHERE duplicate_of IS NOT NULL GROUP BY 1").fetchall())
    for r in rows:
        r["linked_count"] = counts.get(r["id"], 0)
    return rows


@router.get("/reports/{report_id}")
def report_detail(report_id: int):
    with db.connect() as conn:
        return _detail(conn, report_id)


class StatusIn(BaseModel):
    status: str
    assignee: str | None = Field(None, max_length=80)
    note: str | None = Field(None, max_length=300)


@router.patch("/reports/{report_id}/status")
def update_status(report_id: int, body: StatusIn, authorization: str | None = Header(None)):
    _verify_officer(authorization)
    if body.status not in C.STATUSES:
        raise HTTPException(422, f"Status must be one of {C.STATUSES}")
    with db.connect() as conn:
        r = _get(conn, report_id)
        assignee = (body.assignee or "").strip() or r["assignee"]
        if body.status == "Assigned" and not assignee:
            raise HTTPException(422, "Assigned status needs an assignee")
        targets = [report_id] + [x["id"] for x in conn.execute("SELECT id FROM reports WHERE duplicate_of=?", (report_id,))]
        for tid in targets:  # linked duplicates follow their primary so every citizen sees progress
            note = body.note if tid == report_id else f"Update on linked report #{report_id}" + (f": {body.note}" if body.note else "")
            conn.execute("UPDATE reports SET status=?, assignee=? WHERE id=?", (body.status, assignee, tid))
            db.add_event(conn, tid, body.status, note, assignee)
        pipeline.refresh(conn)
        return _detail(conn, report_id)


@router.post("/reports/{report_id}/unlink")
def unlink_duplicate(report_id: int, authorization: str | None = Header(None)):
    _verify_officer(authorization)
    with db.connect() as conn:
        r = _get(conn, report_id)
        if not r["duplicate_of"]:
            raise HTTPException(400, "Report is not linked as a duplicate")
        conn.execute("UPDATE reports SET duplicate_of=NULL, duplicate_score=NULL WHERE id=?", (report_id,))
        db.add_event(conn, report_id, r["status"], f"Unlinked from report #{r['duplicate_of']} by an officer; reviewed on its own")
        pipeline.refresh(conn)
        return _detail(conn, report_id)


# ---------- citizen tracking (public view, no internal scoring) ----------
@router.get("/track/{code}")
def track(code: str):
    with db.connect() as conn:
        r = db.row(conn.execute("SELECT * FROM reports WHERE tracking_code=?", (code.strip().upper(),)).fetchone())
        if not r:
            raise HTTPException(404, "No report with that tracking code")
        return {"tracking_code": r["tracking_code"], "status": r["status"], "category": r["category"], "summary": r["summary"],
                "address": r["address"], "created_at": r["created_at"], "assignee": r["assignee"], "statuses": C.STATUSES,
                "linked_to_existing": bool(r["duplicate_of"]), "events": _events(conn, r["id"]),
                "location_approx": r.get("location_approx", 0),
                "image_url": f"/uploads/{r['image_path']}" if r["image_path"] else None}


# ---------- reveal ----------
@router.get("/clusters")
def clusters():
    with db.connect() as conn:
        out = []
        for c in conn.execute("SELECT * FROM clusters ORDER BY report_count DESC"):
            c = db.row(c)
            c["members"] = [dict(m) for m in conn.execute(
                "SELECT id, summary, category, priority_band, status FROM reports WHERE cluster_id=? ORDER BY priority_score DESC", (c["id"],))]
            out.append(c)
        return out


@router.get("/stats")
def stats():
    with db.connect() as conn:
        rows = [dict(r) for r in conn.execute("SELECT status, priority_band, category, ward, duplicate_of, created_at FROM reports")]
    open_rows = [r for r in rows if r["status"] != "Resolved"]
    start = datetime.now(timezone.utc).date() - timedelta(days=9)
    per_day = Counter(r["created_at"][:10] for r in rows)
    with db.connect() as conn:
        hotspots = conn.execute("SELECT COUNT(*) FROM clusters").fetchone()[0]
    return {
        "total": len(rows), "open": len(open_rows), "hotspots": hotspots,
        "duplicates_linked": sum(1 for r in rows if r["duplicate_of"]),
        "by_status": {s: sum(r["status"] == s for r in rows) for s in C.STATUSES},
        "by_band": {b: sum(r["priority_band"] == b for r in open_rows) for _, b in C.BANDS},
        "by_category": dict(Counter(r["category"] for r in open_rows)),
        "ward_category": [{"ward": w, "category": c, "count": n} for (w, c), n in
                          sorted(Counter((r["ward"], r["category"]) for r in open_rows).items())],
        "per_day": [{"date": str(start + timedelta(days=i)), "count": per_day.get(str(start + timedelta(days=i)), 0)} for i in range(10)],
    }


@router.get("/health")
def health():
    with db.connect() as conn:
        n = conn.execute("SELECT COUNT(*) FROM reports").fetchone()[0]
    ai_mode = "llm" if ai.LLM_STATUS == "ok" else "rules"
    return {
        "ok": True,
        "reports": n,
        "ai_mode": ai_mode,
        "llm_last_error": ai.LLM_LAST_ERROR,
        "embedder": C.EMBEDDER,
        "model": C.LLM_MODEL if ai_mode == "llm" else None,
        "categories": C.CATEGORIES,
        "statuses": C.STATUSES,
    }


@router.post("/demo/reset")
def demo_reset(authorization: str | None = Header(None)):
    """Reload the synthetic demo data (demo convenience; wipes all reports)."""
    _verify_officer(authorization)
    if os.getenv("ALLOW_DEMO_RESET", "0") != "1":
        raise HTTPException(403, "Demo reset disabled")
    return {"seeded": seed_mod.seed()}


app.include_router(router)
app.mount("/uploads", StaticFiles(directory=C.UPLOAD_DIR), name="uploads")
if C.FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=C.FRONTEND_DIST, html=True), name="frontend")
