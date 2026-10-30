"""Database orchestration around the pure AI functions in ai.py."""
import json
import secrets
from datetime import datetime, timezone

from . import ai, config as C, db


def _age_days(created_at: str) -> float:
    return max(0.0, (datetime.now(timezone.utc) - datetime.fromisoformat(created_at)).total_seconds() / 86400)


def find_duplicate(conn, r: dict) -> tuple[int | None, float | None]:
    """Link to the best open primary report with the same category, within DUP_RADIUS_M and similar enough.
    Reports with approximate/inferred locations are excluded from duplicate matching.
    """
    if r.get("location_approx"):
        return None, None
    rows = conn.execute(
        "SELECT id, text, lat, lng FROM reports WHERE duplicate_of IS NULL AND status != 'Resolved' "
        "AND (location_approx = 0 OR location_approx IS NULL) "
        "AND id != ? AND category = ?", (r["id"], r["category"])).fetchall()
    near = [c for c in rows if ai.haversine_m(r["lat"], r["lng"], c["lat"], c["lng"]) <= C.DUP_RADIUS_M]
    if not near:
        return None, None
    corpus = [x["text"] for x in conn.execute("SELECT text FROM reports")]
    sims, embedder = ai.similarities(r["text"], [c["text"] for c in near], corpus)
    best = max(range(len(near)), key=sims.__getitem__)
    return (near[best]["id"], round(sims[best], 3)) if sims[best] >= C.DUP_MIN_SIM[embedder] else (None, None)


def _rescore(conn, cluster_ids: set[int]) -> dict[int, int]:
    """Recompute priority for every unresolved report. Returns id -> score."""
    dup_counts = {r["duplicate_of"]: r["n"] for r in conn.execute(
        "SELECT duplicate_of, COUNT(*) n FROM reports WHERE duplicate_of IS NOT NULL GROUP BY duplicate_of")}
    scores = {}
    updates = []
    for r in conn.execute("SELECT id, signals, created_at, priority_score, priority_band, reasons FROM reports WHERE status != 'Resolved' AND signals IS NOT NULL").fetchall():
        score, band, reasons = ai.priority(json.loads(r["signals"]), dup_counts.get(r["id"], 0),
                                           r["id"] in cluster_ids, _age_days(r["created_at"]))
        scores[r["id"]] = score
        reasons_json = json.dumps(reasons)
        if (r["priority_score"] != score or
            r["priority_band"] != band or
            r["reasons"] != reasons_json):
            updates.append((score, band, reasons_json, r["id"]))
    if updates:
        conn.executemany("UPDATE reports SET priority_score=?, priority_band=?, reasons=? WHERE id=?", updates)
    return scores


def refresh(conn, use_llm: bool = True) -> None:
    """Recompute hotspots, briefs and priorities. Briefs are cached per member set to avoid repeat LLM calls."""
    base = _rescore(conn, set())
    members = [dict(r) | {"base_score": base.get(r["id"], 0)} for r in conn.execute(
        "SELECT id, lat, lng, category, summary FROM reports WHERE duplicate_of IS NULL AND status != 'Resolved' AND (location_approx = 0 OR location_approx IS NULL)")]
    groups = ai.find_clusters(members)
    old = {c["member_key"]: c for c in conn.execute("SELECT member_key, brief, ai_mode FROM clusters")}
    conn.execute("UPDATE reports SET cluster_id=NULL")
    conn.execute("DELETE FROM clusters")
    in_cluster: set[int] = set()
    for g in groups:
        key = ",".join(str(i) for i in sorted(m["id"] for m in g["members"]))
        cached = old.get(key)
        if cached and (cached["ai_mode"] == "llm" or not (use_llm and ai.llm_available())):
            brief, mode = cached["brief"], cached["ai_mode"]
        else:
            brief, mode = ai.make_brief(g) if use_llm else (ai.template_brief(g), "template")
        cid = conn.execute(
            "INSERT INTO clusters(centroid_lat,centroid_lng,radius_m,report_count,categories,ward,member_key,brief,ai_mode) "
            "VALUES(?,?,?,?,?,?,?,?,?)",
            (g["lat"], g["lng"], g["radius_m"], len(g["members"]), json.dumps(g["categories"]), g["ward"], key, brief, mode)).lastrowid
        ids = [m["id"] for m in g["members"]]
        conn.execute(f"UPDATE reports SET cluster_id=? WHERE id IN ({','.join('?' * len(ids))})", (cid, *ids))
        in_cluster.update(ids)
    _rescore(conn, in_cluster)


_CODE_CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O/1/I


def create_report(conn, *, text: str, lat: float, lng: float, address: str | None = None,
                  user_category: str | None = None, image_path: str | None = None,
                  created_at: str | None = None, citizen_session: str | None = None,
                  location_approx: int = 0) -> int:
    """Insert a raw report plus its first timeline event. AI fields are filled by process_report."""
    created = created_at or db.now_iso()
    code = "CIV-" + "".join(secrets.choice(_CODE_CHARS) for _ in range(6))
    rid = conn.execute(
        "INSERT INTO reports(tracking_code,text,image_path,user_category,lat,lng,address,ward,created_at,citizen_session,location_approx) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
        (code, text, image_path, user_category, lat, lng, address, ai.ward_of(lat, lng), created, citizen_session, location_approx)).lastrowid
    db.add_event(conn, rid, "Submitted", "Report received", at=created)
    return rid


def process_report(conn, report_id: int, refresh_now: bool = True, use_llm: bool = True) -> None:
    """Understand -> duplicate check -> hotspot/priority refresh for one stored report."""
    r = dict(conn.execute("SELECT * FROM reports WHERE id=?", (report_id,)).fetchone())
    u = ai.understand(r["text"], r["user_category"]) if use_llm else ai.understand_rules(r["text"], r["user_category"])
    conn.execute("UPDATE reports SET category=?, summary=?, signals=?, ai_mode=? WHERE id=?",
                 (u["category"], u["summary"], json.dumps(u["signals"]), u["ai_mode"], report_id))
    r["category"] = u["category"]
    dup_id, score = find_duplicate(conn, r)
    if dup_id:
        conn.execute("UPDATE reports SET duplicate_of=?, duplicate_score=? WHERE id=?", (dup_id, score, report_id))
        db.add_event(conn, report_id, "Submitted", f"Linked to report #{dup_id} as a likely duplicate")
    if refresh_now:
        refresh(conn, use_llm)
