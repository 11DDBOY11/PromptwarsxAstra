import time
import pytest
from fastapi.testclient import TestClient

from app.main import app, OFFICER_TOKENS, LOGIN_FAILURES, LOGIN_LOCKOUTS


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        login = c.post("/api/auth/officer-login", json={"email": "officer.pwd@mangaluru.gov.in", "password": "officer123"}).json()
        token = login["token"]
        c.headers.update({"Authorization": f"Bearer {token}"})
        c.post("/api/demo/reset")  # known starting state: the 45 seeded reports
        yield c


def test_health_and_seeded(client):
    h = client.get("/api/health").json()
    assert h["ok"] and h["reports"] == 45 and h["ai_mode"] == "rules"


def test_full_journey(client):
    r = client.post("/api/reports", data={"text": "Water flowing into houses, drain blocked near Bunder Road",
                                          "lat": 12.8703, "lng": 74.8419, "address": "Bunder Road"},
                    files={"image": ("p.jpg", b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00", "image/jpeg")})
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

    # 5. Unauthenticated access rejected on guarded endpoints
    with TestClient(app) as unauth:
        assert unauth.patch("/api/reports/1/status", json={"status": "Under review"}).status_code == 401
        assert unauth.post("/api/reports/1/unlink").status_code == 401
        assert unauth.post("/api/demo/reset").status_code == 401


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


def test_approx_location_reports_never_cluster_or_duplicate(client):
    # Submit 3 distinct reports with no GPS in Falnir ward (address only)
    r1 = client.post("/api/reports", data={"text": "Fallen tree branch blocking walkway near Falnir clinic", "address": "Falnir clinic cross"}).json()
    r2 = client.post("/api/reports", data={"text": "Broken transformer sparking near Falnir main road", "address": "Falnir main road"}).json()
    r3 = client.post("/api/reports", data={"text": "Garbage pile accumulating outside Falnir apartments", "address": "Falnir apartments"}).json()

    assert r1["location_approx"] == 1
    assert r2["location_approx"] == 1
    assert r3["location_approx"] == 1

    # None should be marked as duplicate
    assert r1["duplicate_of"] is None
    assert r2["duplicate_of"] is None
    assert r3["duplicate_of"] is None

    # None should belong to a cluster/hotspot
    assert r1["cluster_id"] is None
    assert r2["cluster_id"] is None
    assert r3["cluster_id"] is None

    # Verify track endpoint returns location_approx
    t1 = client.get(f"/api/track/{r1['tracking_code']}").json()
    assert t1["location_approx"] == 1


def test_token_expiry(client):
    # Log in to get fresh token
    login = client.post("/api/auth/officer-login", json={"email": "officer.pwd@mangaluru.gov.in", "password": "officer123"}).json()
    token = login["token"]

    # Verify active
    me_ok = client.get("/api/auth/officer-me", headers={"Authorization": f"Bearer {token}"})
    assert me_ok.status_code == 200

    # Simulate 13 hours passing (exceeding 12-hour lifetime)
    OFFICER_TOKENS[token]["issued_at"] = time.time() - (13 * 3600)

    # Next call must reject with 401
    me_expired = client.get("/api/auth/officer-me", headers={"Authorization": f"Bearer {token}"})
    assert me_expired.status_code == 401
    assert "expired" in me_expired.json()["detail"].lower()


def test_login_throttling(client):
    ip_headers = {"X-Forwarded-For": "203.0.113.42"}
    LOGIN_FAILURES.pop("203.0.113.42", None)
    LOGIN_LOCKOUTS.pop("203.0.113.42", None)

    # 5 failed attempts in succession
    for _ in range(5):
        res = client.post("/api/auth/officer-login", json={"email": "officer.pwd@mangaluru.gov.in", "password": "wrong"}, headers=ip_headers)
        assert res.status_code == 401

    # 6th attempt must be throttled with HTTP 429
    throttled = client.post("/api/auth/officer-login", json={"email": "officer.pwd@mangaluru.gov.in", "password": "officer123"}, headers=ip_headers)
    assert throttled.status_code == 429
    assert "too many" in throttled.json()["detail"].lower()

    # Simulate lockout window expiration
    LOGIN_LOCKOUTS["203.0.113.42"] = time.time() - 1

    # Should succeed after window expires
    ok = client.post("/api/auth/officer-login", json={"email": "officer.pwd@mangaluru.gov.in", "password": "officer123"}, headers=ip_headers)
    assert ok.status_code == 200


def test_magic_byte_upload_validation(client):
    # 1. Invalid content matching MIME type header: spoofed text pretending to be JPEG
    spoofed = client.post("/api/reports", data={"text": "Road issue description valid", "lat": 12.87, "lng": 74.85},
                          files={"image": ("fake.jpg", b"NOT_A_VALID_JPEG_HEADER_TEXT", "image/jpeg")})
    assert spoofed.status_code == 422
    assert "header" in spoofed.json()["detail"].lower() or "magic" in spoofed.json()["detail"].lower()

    # 2. Valid JPEG magic bytes
    valid_jpg = client.post("/api/reports", data={"text": "Road issue description valid", "lat": 12.87, "lng": 74.85},
                            files={"image": ("valid.jpg", b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00", "image/jpeg")})
    assert valid_jpg.status_code == 201

    # 3. Valid PNG magic bytes
    valid_png = client.post("/api/reports", data={"text": "Road issue description valid", "lat": 12.87, "lng": 74.85},
                            files={"image": ("valid.png", b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR", "image/png")})
    assert valid_png.status_code == 201


def test_security_headers_and_cors_hardening(client):
    # 1. Security Headers on responses
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.headers["x-content-type-options"] == "nosniff"
    assert res.headers["x-frame-options"] == "DENY"
    assert res.headers["referrer-policy"] == "no-referrer"
    assert res.headers["permissions-policy"] == "geolocation=(self)"

    # 2. CORS: Unauthorized origin from evil domain gets no allow-origin header
    evil_res = client.get("/api/health", headers={"Origin": "https://evil.example"})
    assert evil_res.headers.get("access-control-allow-origin") is None or evil_res.headers.get("access-control-allow-origin") != "https://evil.example"
    assert evil_res.headers.get("access-control-allow-origin") != "*"

    # 3. Local dev origin allowed
    dev_res = client.get("/api/health", headers={"Origin": "http://localhost:5173"})
    assert dev_res.headers.get("access-control-allow-origin") == "http://localhost:5173"



