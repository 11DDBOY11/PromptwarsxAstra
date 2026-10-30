"""All tunables in one place. Weights and thresholds are judgement calls, not validated values."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Auto-load .env if present (checking backend/.env and root .env)
for env_path in [ROOT / ".env", ROOT.parent / ".env"]:
    if env_path.exists():
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())

DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "civic.db"))
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", ROOT / "data" / "uploads"))
FRONTEND_DIST = ROOT.parent / "frontend" / "dist"

groq_key = os.getenv("GROQ_API_KEY")
anthropic_key = os.getenv("ANTHROPIC_API_KEY")

default_model = "openai/gpt-oss-20b" if (groq_key or not anthropic_key) else "claude-haiku-5-5"
LLM_MODEL = os.getenv("LLM_MODEL") or default_model

FALLBACK_ONLY = os.getenv("FALLBACK_ONLY") == "1"  # force rule-based path
EMBEDDER = os.getenv("EMBEDDER", "tfidf")  # "tfidf" (default) or "st" (sentence-transformers)

CATEGORIES = [
    "drainage_waterlogging", "road_damage", "waste", "streetlight",
    "electrical_hazard", "safety_hazard", "water_supply", "other",
]
STATUSES = ["Submitted", "Under review", "Assigned", "In progress", "Resolved"]
MAX_TEXT, MAX_IMAGE_BYTES = 1000, 5 * 1024 * 1024

# Duplicate detection: same category, within radius, similarity at or above threshold.
DUP_RADIUS_M = 150
# tfidf: on the seed set true duplicates score >= 0.21 and distinct nearby issues <= 0.14 (thin margin).
DUP_MIN_SIM = {"tfidf": 0.18, "st": 0.78}

# Hotspots: DBSCAN over open, non-duplicate reports.
CLUSTER_EPS_M = 200
CLUSTER_MIN = 3

# Priority (0-100 scale, summed). Index = signal level 0..3.
SAFETY_POINTS = [0, 8, 20, 35]
PEOPLE_POINTS = [0, 4, 10, 20]
BLOCKS_POINTS, WORSENING_POINTS = 10, 8
DUP_POINTS, DUP_CAP = 3, 5          # per linked report, capped at DUP_CAP reports
CLUSTER_POINTS = 7
AGE_GRACE_DAYS, AGE_CAP = 3, 10     # +1 per day after grace, capped
CRITICAL_FLOOR = 70                 # safety_risk 3 is raised to at least this
BANDS = [(70, "Critical"), (45, "High"), (20, "Medium"), (0, "Low")]

# Nearest-centroid ward lookup (invented ward centres; real boundaries are a next step).
WARDS = {
    "Bunder": (12.8697, 74.8420), "Kadri": (12.8885, 74.8530), "Kankanady": (12.8640, 74.8590),
    "Bejai": (12.8860, 74.8400), "Attavar": (12.8650, 74.8350), "Falnir": (12.8750, 74.8500),
    "Surathkal": (12.9850, 74.8030), "Ullal": (12.8100, 74.8450),
}

CREW = {
    "drainage_waterlogging": "drain-cleaning crew with a suction pump",
    "road_damage": "road repair team",
    "waste": "solid-waste collection truck",
    "streetlight": "electrical maintenance crew",
    "electrical_hazard": "electricity board emergency crew",
    "safety_hazard": "emergency response team",
    "water_supply": "water supply maintenance crew",
    "other": "ward inspector",
}
