import os
from collections import Counter
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException

from .. import config as C, db, seed as seed_mod
from ..auth_utils import require_officer

router = APIRouter(prefix="/api", tags=["officer"])


@router.get("/clusters")
def clusters(officer: dict = Depends(require_officer)):
    with db.connect() as conn:
        out = []
        for c in conn.execute("SELECT * FROM clusters ORDER BY report_count DESC"):
            c = db.row(c)
            c["members"] = [dict(m) for m in conn.execute(
                "SELECT id, summary, category, priority_band, status FROM reports WHERE cluster_id=? ORDER BY priority_score DESC", (c["id"],))]
            out.append(c)
        return out


@router.get("/stats")
def stats(officer: dict = Depends(require_officer)):
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


@router.post("/demo/reset")
def demo_reset(officer: dict = Depends(require_officer)):
    """Reload the synthetic demo data (demo convenience; wipes all reports)."""
    if os.getenv("ALLOW_DEMO_RESET", "0") != "1":
        raise HTTPException(403, "Demo reset disabled")
    return {"seeded": seed_mod.seed()}
