import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
import time
from fastapi import Header, HTTPException, Request

TOKEN_MAX_AGE_SECONDS = 12 * 3600  # 12 hours

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    logging.warning("SECRET_KEY not set in environment; generated random secret. Officer tokens will invalidate across server restarts.")
    SECRET_KEY = secrets.token_hex(32)
_SECRET_BYTES = SECRET_KEY.encode("utf-8")


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _b64url_decode(s: str) -> bytes:
    padding = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + padding)


def create_officer_token(officer_data: dict, ttl: int = TOKEN_MAX_AGE_SECONDS) -> str:
    payload = {
        "sub": officer_data["email"],
        "exp": int(time.time() + ttl),
        "officer": officer_data,
    }
    payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    payload_b64 = _b64url_encode(payload_bytes)
    sig = hmac.new(_SECRET_BYTES, payload_b64.encode("utf-8"), hashlib.sha256).digest()
    sig_b64 = _b64url_encode(sig)
    return f"{payload_b64}.{sig_b64}"


def verify_officer_token(token: str) -> dict:
    parts = token.split(".")
    if len(parts) != 2:
        raise HTTPException(401, "Invalid token format")
    payload_b64, sig_b64 = parts
    expected_sig = hmac.new(_SECRET_BYTES, payload_b64.encode("utf-8"), hashlib.sha256).digest()
    expected_sig_b64 = _b64url_encode(expected_sig)
    if not hmac.compare_digest(sig_b64, expected_sig_b64):
        raise HTTPException(401, "Invalid token signature")
    try:
        payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
    except Exception:
        raise HTTPException(401, "Invalid token payload")
    if time.time() > payload.get("exp", 0):
        raise HTTPException(401, "Token expired (12-hour lifetime). Please sign in again.")
    officer = payload.get("officer")
    if not officer:
        raise HTTPException(401, "Invalid token claims")
    return officer


def require_officer(authorization: str | None = Header(None)) -> dict:
    """FastAPI dependency requiring a valid municipal officer token."""
    if not authorization:
        raise HTTPException(401, "Officer authorization required. Please sign in to the Officer Portal.")
    if authorization.startswith("Bearer "):
        token = authorization.split("Bearer ", 1)[1].strip()
    else:
        token = authorization.strip()
    return verify_officer_token(token)


# Rate limiting for officer login: 5 failed attempts per client IP within 60s -> 429 for next 60s
LOGIN_FAILURES: dict[str, list[float]] = {}
LOGIN_LOCKOUTS: dict[str, float] = {}


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"


def _hash_pw(password: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000).hex()


DEMO_OFFICERS = {
    "officer.pwd@mangaluru.gov.in": {
        "salt": bytes.fromhex("240cd35fc811ff0d531a6f2d99e20eda"),
        "pw_hash": "1d3a6d0e437bea941e92cf7b91d4f2454ef8017afc0cbffd21c2ebf346a011a7",
        "name": "Inspector B. Shetty",
        "department": "Road Infrastructure (PWD)",
        "ward": "Kadri & Central Mangaluru",
        "role": "officer",
    },
    "officer.drainage@mangaluru.gov.in": {
        "salt": bytes.fromhex("cf48c11a014c67d04441bda01c0d4b81"),
        "pw_hash": "7b02897892ec495f7978d7d0db5d60e26bee44eecbc82b930645faa4dc18a3da",
        "name": "Engineer K. Poojary",
        "department": "Stormwater Drainage & Sanitation",
        "ward": "Bunder & Port Area",
        "role": "officer",
    },
    "officer.admin@mangaluru.gov.in": {
        "salt": bytes.fromhex("94271bf4f9f1e3acffc2691dbde34eba"),
        "pw_hash": "33f73f89c4c2b5745a3db5e3a625e2db1fc1e3d04c160ba29a4e01347e3878f9",
        "name": "Commissioner Rai",
        "department": "Mangaluru City Corporation Administration",
        "ward": "All Wards",
        "role": "officer",
    },
}

_pwd_override = os.getenv("DEMO_OFFICER_PWD_PASSWORD") or os.getenv("DEMO_OFFICER_PASSWORD")
if _pwd_override:
    DEMO_OFFICERS["officer.pwd@mangaluru.gov.in"]["pw_hash"] = _hash_pw(
        _pwd_override, DEMO_OFFICERS["officer.pwd@mangaluru.gov.in"]["salt"]
    )

_drainage_override = os.getenv("DEMO_OFFICER_DRAINAGE_PASSWORD") or os.getenv("DEMO_OFFICER_PASSWORD")
if _drainage_override:
    DEMO_OFFICERS["officer.drainage@mangaluru.gov.in"]["pw_hash"] = _hash_pw(
        _drainage_override, DEMO_OFFICERS["officer.drainage@mangaluru.gov.in"]["salt"]
    )

_admin_override = os.getenv("DEMO_OFFICER_ADMIN_PASSWORD") or os.getenv("DEMO_OFFICER_PASSWORD")
if _admin_override:
    DEMO_OFFICERS["officer.admin@mangaluru.gov.in"]["pw_hash"] = _hash_pw(
        _admin_override, DEMO_OFFICERS["officer.admin@mangaluru.gov.in"]["salt"]
    )
