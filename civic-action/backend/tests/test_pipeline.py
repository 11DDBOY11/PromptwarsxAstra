import pytest

from app import ai, db, pipeline, seed


@pytest.fixture(scope="module")
def seeded():
    assert seed.seed() == 45
    with db.connect() as conn:
        yield conn


def test_seed_size(seeded):
    assert seeded.execute("SELECT COUNT(*) FROM reports").fetchone()[0] == 45


def test_categories():
    assert ai.understand_rules("Open manhole outside the school", None)["category"] == "safety_hazard"
    assert ai.understand_rules("Kachra bin overflowing", None)["category"] == "waste"
    assert ai.understand_rules("something odd happened", "road_damage")["category"] == "road_damage"
    assert ai.understand_rules("something odd happened", None)["category"] == "other"


def test_duplicate_groups_link_to_one_primary(seeded):
    pot = [db.row(r) for r in seeded.execute(
        "SELECT * FROM reports WHERE category='road_damage' AND address LIKE 'Kadri%'")]
    assert len(pot) == 4
    primaries = [r for r in pot if r["duplicate_of"] is None]
    assert len(primaries) == 1 and all(r["duplicate_of"] == primaries[0]["id"] for r in pot if r is not primaries[0])
    bins = [db.row(r) for r in seeded.execute("SELECT * FROM reports WHERE address LIKE 'Kankanady%'")]
    assert len(bins) == 3 and sum(r["duplicate_of"] is None for r in bins) == 1


def test_near_misses_are_not_merged(seeded):
    far_pothole = db.row(seeded.execute("SELECT * FROM reports WHERE address LIKE 'Bejai main road%'").fetchone())
    far_bin = db.row(seeded.execute("SELECT * FROM reports WHERE address LIKE 'Attavar (2 km%'").fetchone())
    assert far_pothole["duplicate_of"] is None and far_bin["duplicate_of"] is None
    street = db.row(seeded.execute("SELECT * FROM reports WHERE text LIKE 'Streetlight not working near Bunder%'").fetchone())
    assert street["duplicate_of"] is None and street["category"] == "streetlight"


def test_urgent_items_are_critical_and_explained(seeded):
    rows = [db.row(r) for r in seeded.execute("SELECT * FROM reports WHERE priority_band='Critical'")]
    assert len(rows) == 3
    assert all(r["priority_score"] >= 70 and r["reasons"] for r in rows)
    assert any("Immediate danger" in x for r in rows for x in r["reasons"])


def test_priority_reasons_sum_to_score():
    sig = {"safety_risk": 2, "people_affected": 2, "blocks_access": True, "worsening": False, "evidence": {}}
    score, band, reasons = ai.priority(sig, dup_count=2, in_cluster=True, age_days=5)
    assert score == 20 + 10 + 10 + 6 + 7 + 2 and len(reasons) == 6 and band == "High"


def test_hotspot_found_with_mixed_categories(seeded):
    big = db.row(seeded.execute("SELECT * FROM clusters ORDER BY report_count DESC").fetchone())
    assert big["ward"] == "Bunder" and big["report_count"] >= 6 and len(big["categories"]) >= 2 and big["brief"]
    reasons = [r[0] for r in seeded.execute("SELECT reasons FROM reports WHERE cluster_id=?", (big["id"],))]
    assert all("part of a hotspot" in r for r in reasons)


def test_new_report_joins_hotspot_and_links_duplicate(seeded):
    before = seeded.execute("SELECT report_count FROM clusters ORDER BY report_count DESC").fetchone()[0]
    rid = pipeline.create_report(seeded, text="Water flowing into houses, drain blocked near Bunder Road",
                                 lat=12.8703, lng=74.8419, address="Bunder Road")
    pipeline.process_report(seeded, rid, use_llm=False)
    r = db.row(seeded.execute("SELECT * FROM reports WHERE id=?", (rid,)).fetchone())
    assert r["category"] == "drainage_waterlogging" and r["summary"] and r["reasons"]
    assert r["cluster_id"] is not None or r["duplicate_of"] is not None
    after = seeded.execute("SELECT report_count FROM clusters ORDER BY report_count DESC").fetchone()[0]
    assert after >= before


def test_llm_garbage_output_falls_back(monkeypatch):
    monkeypatch.setattr(ai, "_llm_json", lambda *a, **k: {"category": "not-a-category", "summary": ""})
    assert ai.understand_llm("x", None) is None
    assert ai.understand("Open manhole near school", None)["ai_mode"] == "rules"


def test_llm_valid_output_is_validated_and_clamped(monkeypatch):
    good = {"category": "road_damage", "summary": "Deep pothole near the signal", "safety_risk": 9,
            "people_affected": "2", "blocks_access": 1, "worsening": 0, "evidence": {"safety_risk": "bikes falling"}}
    monkeypatch.setattr(ai, "_llm_json", lambda *a, **k: good)
    u = ai.understand_llm("pothole", None)
    assert u["ai_mode"] == "llm" and u["signals"]["safety_risk"] == 3 and u["signals"]["people_affected"] == 2
    assert u["signals"]["blocks_access"] is True and u["signals"]["worsening"] is False


def test_kannada_and_regional_category_rules():
    assert ai.understand_rules("ರಸ್ತೆಯಲ್ಲಿ ದೊಡ್ಡ ಗುಂಡಿ ಬಿದ್ದಿದೆ", None)["category"] == "road_damage"
    assert ai.understand_rules("ಚರಂಡಿ ನೀರು ತುಂಬಿ ರಸ್ತೆಗೆ ಹರಿಯುತ್ತಿದೆ", None)["category"] == "drainage_waterlogging"
    assert ai.understand_rules("ಕಸದ ತೊಟ್ಟಿ ತುಂಬಿ ನಾರುತ್ತಿದೆ", None)["category"] == "waste"
    assert ai.understand_rules("ಬೀದಿ ದೀಪ ಉರಿಯುತ್ತಿಲ್ಲ, ಕತ್ತಲೆಯಾಗಿದೆ", None)["category"] == "streetlight"
    assert ai.understand_rules("ವಿದ್ಯುತ್ ತಂತಿ ತುಂಡಾಗಿ ಬಿದ್ದಿದೆ", None)["category"] == "electrical_hazard"
    assert ai.understand_rules("ಕುಡಿಯುವ ನೀರು ಬರುತ್ತಿಲ್ಲ", None)["category"] == "water_supply"

    # Transliterated Kannada & Mangaluru terms
    assert ai.understand_rules("Big road gundi near market", None)["category"] == "road_damage"
    assert ai.understand_rules("Mori and kaluve blocked completely", None)["category"] == "drainage_waterlogging"
    assert ai.understand_rules("Street deepa not working", None)["category"] == "streetlight"
    assert ai.understand_rules("Kasa dumped on roadside", None)["category"] == "waste"

