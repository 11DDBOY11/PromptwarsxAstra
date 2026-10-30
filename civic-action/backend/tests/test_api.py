import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        c.post("/api/demo/reset")  # known starting state: the 45 seeded reports
        yield c


def test_health_and_seeded(client):
    h = client.get("/api/health").json()
    assert h["ok"] and h["reports"] == 45 and h["ai_mode"] == "rules"


def test_full_journey(client):
    r = client.post("/api/reports", data={"text": "Water flowing into houses, drain blocked near Bunder Road",
                                          "lat": 12.8703, "lng": 74.8419, "address": "Bunder Road"},
                    files={"image": ("p.jpg", b"\xff\xd8\xff fake", "image/jpeg")})
    assert r.status_code == 201
    rep = r.json()
    assert rep["category"] == "drainage_waterlogging" and rep["reasons"] and rep["image_url"]
    code, rid = rep["tracking_code"], rep["id"]

    # officer must give an assignee before Assigned
    assert client.patch(f"/api/reports/{rid}/status", json={"status": "Assigned"}).status_code == 422
    ok = client.patch(f"/api/reports/{rid}/status", json={"status": "Assigned", "assignee": "Ward 12 drain crew"})
    assert ok.status_code == 200
    client.patch(f"/api/reports/{rid}/status", json={"status": "In progress", "note": "Crew on site"})

    t = client.get(f"/api/track/{code}").json()
    assert t["status"] == "In progress" and t["assignee"] == "Ward 12 drain crew"
    assert [e["status"] for e in t["events"]][-2:] == ["Assigned", "In progress"]
    assert "priority_score" not in t  # internal scoring is not exposed to citizens


def test_duplicates_follow_primary_and_can_be_unlinked(client):
    reports = client.get("/api/reports?include_duplicates=true").json()
    dup = next(r for r in reports if r["duplicate_of"] and "Kadri" in (r["address"] or ""))
    primary = next(r for r in reports if r["id"] == dup["duplicate_of"])
    client.patch(f"/api/reports/{primary['id']}/status", json={"status": "Under review"})
    assert client.get(f"/api/track/{dup['tracking_code']}").json()["status"] == "Under review"
    after = client.post(f"/api/reports/{dup['id']}/unlink").json()
    assert after["duplicate_of"] is None
    assert client.post(f"/api/reports/{dup['id']}/unlink").status_code == 400


def test_validation(client):
    bad = [{"text": "ab", "lat": 1, "lng": 1}, {"text": "valid text here", "lat": 99, "lng": 1},
           {"text": "valid text here", "lat": 1, "lng": 1, "category": "nope"}]
    assert all(client.post("/api/reports", data=d).status_code == 422 for d in bad)
    r = client.post("/api/reports", data={"text": "valid text here", "lat": 1, "lng": 1},
                    files={"image": ("x.exe", b"MZ", "application/octet-stream")})
    assert r.status_code == 422
    assert client.get("/api/track/NOPE").status_code == 404


def test_reveal_endpoints(client):
    stats = client.get("/api/stats").json()
    assert stats["hotspots"] >= 1 and stats["ward_category"] and len(stats["per_day"]) == 10
    cl = client.get("/api/clusters").json()
    assert cl[0]["brief"] and cl[0]["members"]


def test_officer_authentication(client):
    # 1. Invalid login
    res_bad = client.post("/api/auth/officer-login", json={"email": "officer.pwd@mangaluru.gov.in", "password": "wrongpassword"})
    assert res_bad.status_code == 401

    res_unknown = client.post("/api/auth/officer-login", json={"email": "nobody@mangaluru.gov.in", "password": "any"})
    assert res_unknown.status_code == 401

    # 2. Valid login
    res_ok = client.post("/api/auth/officer-login", json={"email": "officer.pwd@mangaluru.gov.in", "password": "officer123"})
    assert res_ok.status_code == 200
    data = res_ok.json()
    token = data["token"]
    assert token.startswith("mcc-")
    assert data["officer"]["name"] == "Inspector B. Shetty"
    assert data["officer"]["role"] == "officer"

    # 3. Verify officer-me endpoint with token
    me = client.get("/api/auth/officer-me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["officer"]["email"] == "officer.pwd@mangaluru.gov.in"

    # 4. Bad token
    me_bad = client.get("/api/auth/officer-me", headers={"Authorization": "Bearer invalid-token"})
    assert me_bad.status_code == 401


def test_citizen_session_tracking_and_recovery(client):
    session_id = "test_cit_session_998877"
    r = client.post("/api/reports", data={
        "text": "Open drainage manhole without cover near school",
        "lat": 12.872, "lng": 74.843,
        "address": "Bunder school cross",
        "citizen_session": session_id,
    })
    assert r.status_code == 201
    code = r.json()["tracking_code"]

    # Retrieve all reports for this device session
    sess_res = client.get(f"/api/reports/by-session?session_id={session_id}")
    assert sess_res.status_code == 200
    reports = sess_res.json()
    assert len(reports) >= 1
    assert any(x["tracking_code"] == code for x in reports)


def test_address_text_infers_ward_coordinates(client):
    # Omit lat and lng completely, provide Kadri in address text
    r = client.post("/api/reports", data={
        "text": "Deep road crater causing vehicles to swerve near Kadri market",
        "address": "Kadri temple road",
    })
    assert r.status_code == 201
    rep = r.json()
    assert rep["ward"] == "Kadri"
    assert abs(rep["lat"] - 12.8885) < 0.001
    assert abs(rep["lng"] - 74.8530) < 0.001


def test_kannada_language_complaint_intake(client):
    # Kannada complaint input
    kannada_text = "ರಸ್ತೆಯಲ್ಲಿ ದೊಡ್ಡ ಗುಂಡಿ ಬಿದ್ದಿದೆ, ಬೈಕ್ ಸವಾರರು ಬೀಳುತ್ತಿದ್ದಾರೆ"
    r = client.post("/api/reports", data={
        "text": kannada_text,
        "address": "Bejai circle",
    })
    assert r.status_code == 201
    rep = r.json()
    assert rep["category"] == "road_damage"
    assert rep["ward"] == "Bejai"
    assert rep["tracking_code"].startswith("CIV-")

