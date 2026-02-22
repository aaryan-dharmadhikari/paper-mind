import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

LITELLM_MODEL = os.getenv("LITELLM_MODEL", "openai/gpt-4o-mini")
DB_PATH = os.getenv("DB_PATH", str(BASE_DIR / "paper_mind.db"))
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

NICEGUI_HOST = os.getenv("NICEGUI_HOST", "0.0.0.0")
NICEGUI_PORT = int(os.getenv("NICEGUI_PORT", "8080"))
