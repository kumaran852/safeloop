import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.getenv("SAFELOOP_DATA_DIR", str(ROOT / "data")))
DATA_DIR.mkdir(parents=True, exist_ok=True)
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{(DATA_DIR / 'safeloop.db').as_posix()}")
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if o.strip()]
AUTO_SEED = os.getenv("SAFELOOP_AUTO_SEED", "1") != "0"
MAX_BODY_BYTES = 100_000

REGION_LABELS = {
    "neck": "Neck",
    "shoulder": "Shoulder",
    "upper_back": "Upper back",
    "lower_back": "Lower back",
    "elbow_wrist_hand": "Elbow / wrist / hand",
    "hip_thigh": "Hip / thigh",
    "knee": "Knee",
    "ankle_foot": "Ankle / foot",
}
BODY_REGIONS = list(REGION_LABELS)
SHIFT_TYPES = ["Morning", "Afternoon", "Night"]
DEFAULT_TASKS = ["Waste Collection", "Street Sweeping", "Loading", "Drain Cleaning", "Waste Segregation"]
LEVELS = ["Low", "Moderate", "High", "Critical"]
