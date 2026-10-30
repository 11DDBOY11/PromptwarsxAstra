import hmac
import time
from fastapi import APIRouter, Depends, HTTPException, Request

from ..auth_utils import (
    DEMO_OFFICERS,
    LOGIN_FAILURES,
    LOGIN_LOCKOUTS,
    _get_client_ip,
    _hash_pw,
    create_officer_token,
    require_officer,
)
from ..schemas import LoginIn

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/officer-login")
def officer_login(body: LoginIn, request: Request):
    client_ip = _get_client_ip(request)
    now = time.time()

    # Check IP lockout
    lockout_until = LOGIN_LOCKOUTS.get(client_ip, 0)
    if now < lockout_until:
        raise HTTPException(429, "Too many failed officer login attempts. Please wait 60 seconds.")

    email = body.email.strip().lower()
    acc = DEMO_OFFICERS.get(email)
    valid_pw = False
    if acc:
        supplied_hash = _hash_pw(body.password, acc["salt"])
        valid_pw = hmac.compare_digest(supplied_hash, acc["pw_hash"])

    if not acc or not valid_pw:
        failures = [t for t in LOGIN_FAILURES.get(client_ip, []) if now - t <= 60]
        failures.append(now)
        LOGIN_FAILURES[client_ip] = failures
        if len(failures) >= 5:
            LOGIN_LOCKOUTS[client_ip] = now + 60
            LOGIN_FAILURES[client_ip] = []
        raise HTTPException(401, "Invalid municipal officer credentials")

    LOGIN_FAILURES.pop(client_ip, None)
    LOGIN_LOCKOUTS.pop(client_ip, None)

    info = {
        "email": email,
        "name": acc["name"],
        "department": acc["department"],
        "ward": acc["ward"],
        "role": "officer",
    }
    token = create_officer_token(info)
    return {"token": token, "officer": info}


@router.get("/officer-me")
def officer_me(officer: dict = Depends(require_officer)):
    return {"ok": True, "officer": officer}
