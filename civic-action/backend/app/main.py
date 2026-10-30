from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles

from . import ai, config as C, db, seed as seed_mod
from .auth_utils import (
    DEMO_OFFICERS,
    LOGIN_FAILURES,
    LOGIN_LOCKOUTS,
    SECRET_KEY,
    TOKEN_MAX_AGE_SECONDS,
    create_officer_token,
    require_officer,
    verify_officer_token,
)
from .routers import auth, officer, public, reports
from .routers.reports import REPORT_SUBMISSIONS


@asynccontextmanager
async def lifespan(_: FastAPI):
    C.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    C.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    db.init_db()
    with db.connect() as conn:
        empty = conn.execute("SELECT COUNT(*) FROM reports").fetchone()[0] == 0
    if empty:
        seed_mod.seed()  # first run: load the synthetic demo set
    ai.check_llm_health()
    yield


app = FastAPI(title="Civic Action Platform", lifespan=lifespan)

app.add_middleware(GZipMiddleware, minimum_size=1000)

# Allow only Vite dev server local origins; frontend is served from same origin in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "geolocation=(self)"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "img-src 'self' data: blob:; "
        "style-src 'self' 'unsafe-inline'; "
        "script-src 'self'; "
        "connect-src 'self'; "
        "frame-ancestors 'none'"
    )

    path = request.url.path
    if path.startswith("/assets/"):
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    elif path in ("/", "/index.html", "/sw.js") or path.endswith(("/index.html", "/sw.js")):
        response.headers["Cache-Control"] = "no-cache"

    return response


# Include modular routers
app.include_router(public.router)
app.include_router(auth.router)
app.include_router(reports.router)
app.include_router(officer.router)

# Mount static files
app.mount("/uploads", StaticFiles(directory=C.UPLOAD_DIR), name="uploads")
if C.FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=C.FRONTEND_DIST, html=True), name="frontend")
