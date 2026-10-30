import json
import re
import time
import uuid
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool

from .. import config as C, db, pipeline
from ..auth_utils import _get_client_ip, require_officer
from ..schemas import StatusIn

router = APIRouter(prefix="/api", tags=["reports"])

IMAGE_EXT = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/gif": ".gif"}

# Rate limiting for citizen report submissions: 10 per minute per IP
REPORT_SUBMISSIONS: dict[str, list[float]] = {}
SESSION_REGEX = re.compile(r"^[a-zA-Z0-9_-]{16,64}$")


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


def _save_and_process_report(text: str, lat: float, lng: float, address: str | None,
                             category: str | None, image_name: str | None,
                             citizen_session: str | None, location_approx: int) -> dict:
    with db.connect() as conn:
        rid = pipeline.create_report(conn, text=text, lat=lat, lng=lng, address=address,
                                     user_category=category, image_path=image_name,
                                     citizen_session=citizen_session,
                                     location_approx=location_approx)
        pipeline.process_report(conn, rid)
        return _detail(conn, rid)


# ---------- capture ----------
@router.post("/reports", status_code=201)
async def submit_report(request: Request,
                        text: str = Form(...), lat: float | None = Form(None), lng: float | None = Form(None),
                        address: str | None = Form(None), category: str | None = Form(None),
                        citizen_session: str | None = Form(None),
                        image: UploadFile | None = File(None)):
    cl = request.headers.get("content-length")
    if cl and int(cl) > 6 * 1024 * 1024:
        raise HTTPException(413, "Request payload too large")

    client_ip = _get_client_ip(request)
    now = time.time()
    submissions = [t for t in REPORT_SUBMISSIONS.get(client_ip, []) if now - t < 60]
    if len(submissions) >= 10:
        raise HTTPException(429, "Too many report submissions. Rate limit is 10 reports per minute per IP.")
    submissions.append(now)
    REPORT_SUBMISSIONS[client_ip] = submissions

    if citizen_session:
        citizen_session = citizen_session.strip()
        if not SESSION_REGEX.match(citizen_session):
            raise HTTPException(422, "Invalid citizen session token format")

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

    return await run_in_threadpool(
        _save_and_process_report,
        text=text,
        lat=lat,
        lng=lng,
        address=(address or "").strip()[:200] or None,
        category=category or None,
        image_name=image_name,
        citizen_session=citizen_session,
        location_approx=location_approx,
    )


@router.get("/reports/by-session")
def get_reports_by_session(session_id: str):
    session_id = (session_id or "").strip()
    if not SESSION_REGEX.match(session_id):
        raise HTTPException(422, "Valid citizen session token required (16-64 chars)")
    with db.connect() as conn:
        rows = [_out(db.row(r)) for r in conn.execute(
            "SELECT * FROM reports WHERE citizen_session=? ORDER BY id DESC", (session_id,))]
    return rows


# ---------- officer views & triage ----------
@router.get("/reports")
def list_reports(
    status: str | None = None,
    include_duplicates: bool = False,
    limit: int = 200,
    offset: int = 0,
    officer: dict = Depends(require_officer),
):
    limit = max(1, min(limit, 500))
    offset = max(0, offset)
    sql, args = "SELECT * FROM reports WHERE 1=1", []
    if status:
        sql += " AND status=?"; args.append(status)
    if not include_duplicates:
        sql += " AND duplicate_of IS NULL"
    sql += " ORDER BY (status='Resolved'), priority_score DESC, created_at LIMIT ? OFFSET ?"
    args.extend([limit, offset])
    with db.connect() as conn:
        rows = [_out(db.row(r)) for r in conn.execute(sql, args)]
        counts = dict(conn.execute("SELECT duplicate_of, COUNT(*) FROM reports WHERE duplicate_of IS NOT NULL GROUP BY 1").fetchall())
    for r in rows:
        r["linked_count"] = counts.get(r["id"], 0)
    return rows


@router.get("/reports/{report_id}")
def report_detail(report_id: int, officer: dict = Depends(require_officer)):
    with db.connect() as conn:
        return _detail(conn, report_id)


@router.patch("/reports/{report_id}/status")
def update_status(report_id: int, body: StatusIn, officer: dict = Depends(require_officer)):
    if body.status not in C.STATUSES:
        raise HTTPException(422, f"Status must be one of {C.STATUSES}")
    with db.connect() as conn:
        r = _get(conn, report_id)
        assignee = (body.assignee or "").strip() or r["assignee"]
        if body.status == "Assigned" and not assignee:
            raise HTTPException(422, "Assigned status needs an assignee")
        targets = [report_id] + [x["id"] for x in conn.execute("SELECT id FROM reports WHERE duplicate_of=?", (report_id,))]
        for tid in targets:
            note = body.note if tid == report_id else f"Update on linked report #{report_id}" + (f": {body.note}" if body.note else "")
            conn.execute("UPDATE reports SET status=?, assignee=? WHERE id=?", (body.status, assignee, tid))
            db.add_event(conn, tid, body.status, note, assignee)
        pipeline.refresh(conn)
        return _detail(conn, report_id)


@router.post("/reports/{report_id}/unlink")
def unlink_duplicate(report_id: int, officer: dict = Depends(require_officer)):
    with db.connect() as conn:
        r = _get(conn, report_id)
        if not r["duplicate_of"]:
            raise HTTPException(400, "Report is not linked as a duplicate")
        conn.execute("UPDATE reports SET duplicate_of=NULL, duplicate_score=NULL WHERE id=?", (report_id,))
        db.add_event(conn, report_id, r["status"], f"Unlinked from report #{r['duplicate_of']} by an officer; reviewed on its own")
        pipeline.refresh(conn)
        return _detail(conn, report_id)
