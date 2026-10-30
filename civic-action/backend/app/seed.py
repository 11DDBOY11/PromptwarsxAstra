"""Synthetic demo data: 45 reports with planted duplicates, urgent issues and one geographic cluster.
All text and coordinates are invented (around Mangaluru ward names); no personal data.
Run:  python -m app.seed
"""
from datetime import datetime, timedelta, timezone

from . import ai, db, pipeline

# (text, lat, lng, address, age_days)
CLUSTER = [  # 6 distinct problems within ~100 m of Bunder Road -> one hotspot
    ("The drain near Bunder Road is completely blocked with plastic and silt, water is not flowing.", 12.8700, 74.8420, "Bunder Road", 2.0),
    ("Knee-deep water on Bunder Road after rain, shops are flooding.", 12.8704, 74.8424, "Bunder Road", 1.5),
    ("Big potholes on Bunder Road filled with muddy water, bikes skidding.", 12.8697, 74.8416, "Bunder Road", 1.2),
    ("Water entering ground floor houses near Bunder Road junction and rising, since morning.", 12.8706, 74.8418, "Bunder Road junction", 0.8),
    ("Open drain slab broken on Bunder Road, bad smell and mosquitoes breeding.", 12.8695, 74.8426, "Bunder Road", 1.8),
    ("Road surface washed away near Bunder Road bus stop, deep crater forming.", 12.8702, 74.8428, "Bunder Road bus stop", 0.6),
]
DUP_POTHOLE = [  # same pothole, different wording (one Hinglish)
    ("Large pothole on Kadri Temple Road near the signal, dangerous for two-wheelers.", 12.8885, 74.8530, "Kadri Temple Road", 3.0),
    ("There is a deep gadda on Kadri temple road by the traffic signal, bike riders are falling.", 12.8886, 74.8532, "Kadri Temple Road", 2.5),
    ("Pothole near Kadri signal on temple road, needs urgent repair.", 12.8884, 74.8529, "Kadri Temple Road", 2.0),
    ("Kadri Temple Road pothole near traffic signal, vehicles swerving to avoid it.", 12.8887, 74.8531, "Kadri Temple Road", 1.0),
]
DUP_BIN = [  # same overflowing bin, 30-60 m apart
    ("Garbage bin overflowing near Kankanady market, waste spilling onto the road.", 12.8640, 74.8590, "Kankanady market", 2.0),
    ("Waste bin overflowing at Kankanady market gate, rotten smell and stray dogs.", 12.8643, 74.8591, "Kankanady market gate", 1.5),
    ("Kachra bin full and overflowing near Kankanady market entrance.", 12.8637, 74.8588, "Kankanady market entrance", 1.0),
]
URGENT = [
    ("Open manhole without cover right outside Bejai school gate, children walk here.", 12.8860, 74.8400, "Bejai school gate", 0.3),
    ("Live electric wire hanging low from a broken pole on Attavar road, sparking.", 12.8650, 74.8350, "Attavar road", 0.2),
    ("Huge tree fallen across Falnir road blocking traffic, branches on the power line.", 12.8750, 74.8500, "Falnir road", 0.1),
]
NEAR_MISS = [  # look like existing reports but must NOT be merged
    ("Large pothole on Kadri Temple Road near the signal, dangerous for two-wheelers.", 12.9020, 74.8400, "Bejai main road (2 km from the Kadri pothole)", 0.5),
    ("Garbage bin overflowing near Kankanady market, waste spilling onto the road.", 12.8500, 74.8300, "Attavar (2 km from the Kankanady bin)", 0.5),
    ("Streetlight not working near Bunder Road junction.", 12.8701, 74.8421, "Bunder Road junction", 0.4),
]
LOCALITIES = ["Hampankatta", "Lalbagh", "Pumpwell", "Jyothi", "Balmatta", "Kodialbail", "Urwa", "Kottara", "Kavoor",
              "Bondel", "Kuloor", "Jeppu", "Derebail", "Mannagudda", "Yeyyadi", "Padil", "Shaktinagar", "Vamanjoor",
              "Bolar", "Hoige Bazar", "Pandeshwar", "Mangaladevi", "Bokkapatna", "Kudroli", "Light House Hill", "Car Street"]
ROUTINE_TEMPLATES = [
    "Streetlight pole near {loc} has not been working for several days, the area is dark at night.",
    "Garbage has not been collected in {loc} for three days, bags piling up near the junction.",
    "Small potholes on the main road at {loc} slow down traffic.",
    "No water supply in {loc} since morning, residents are waiting for a tanker.",
]
PLANTED = CLUSTER + DUP_POTHOLE + DUP_BIN + URGENT + NEAR_MISS


def _routine() -> list[tuple]:
    """26 routine reports on a sparse grid (>= 500 m from every planted point); the last 6 are 4-9 days old."""
    grid = [(12.845 + r * 0.009, 74.790 + c * 0.010) for r in range(6) for c in range(7)]
    far = [(la, ln) for la, ln in grid
           if all(ai.haversine_m(la, ln, p[1], p[2]) >= 500 for p in PLANTED)][:len(LOCALITIES)]
    out = []
    for i, ((la, ln), loc) in enumerate(zip(far, LOCALITIES)):
        age = 4 + (i - 20) * 1.0 if i >= 20 else (i % 3) * 0.7
        out.append((ROUTINE_TEMPLATES[i % 4].format(loc=loc), round(la, 5), round(ln, 5), loc, age))
    return out


def all_reports() -> list[tuple]:
    return PLANTED + _routine()


def seed(use_llm: bool = False) -> int:
    """Reset the database and load the demo set oldest-first so duplicates link to their primary.
    use_llm only affects per-report understanding; cluster briefs always try the LLM once at the end."""
    db.reset_db()
    now = datetime.now(timezone.utc)
    items = sorted(all_reports(), key=lambda x: -x[4])
    with db.connect() as conn:
        for text, lat, lng, addr, age in items:
            created = (now - timedelta(days=age)).isoformat(timespec="seconds")
            rid = pipeline.create_report(conn, text=text, lat=lat, lng=lng, address=addr, created_at=created)
            pipeline.process_report(conn, rid, refresh_now=False, use_llm=use_llm)
        pipeline.refresh(conn, use_llm=True)
    return len(items)


if __name__ == "__main__":
    import sys
    n = seed(use_llm="--llm" in sys.argv)
    print(f"Seeded {n} synthetic reports into {db.C.DB_PATH}")
