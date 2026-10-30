from fastapi import APIRouter, HTTPException

from .. import ai, config as C, db
from .reports import _events

router = APIRouter(prefix="/api", tags=["public"])


@router.get("/track/{code}")
def track(code: str):
    with db.connect() as conn:
        r = db.row(conn.execute("SELECT * FROM reports WHERE tracking_code=?", (code.strip().upper(),)).fetchone())
        if not r:
            raise HTTPException(404, "No report with that tracking code")
        return {
            "tracking_code": r["tracking_code"],
            "status": r["status"],
            "category": r["category"],
            "summary": r["summary"],
            "address": r["address"],
            "created_at": r["created_at"],
            "assignee": r["assignee"],
            "statuses": C.STATUSES,
            "linked_to_existing": bool(r["duplicate_of"]),
            "events": _events(conn, r["id"]),
            "location_approx": r.get("location_approx", 0),
            "image_url": f"/uploads/{r['image_path']}" if r["image_path"] else None,
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
