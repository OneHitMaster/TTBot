"""Konfiguration aus Umgebungsvariablen."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Pfade
BASE_DIR = Path(__file__).resolve().parent
IDEAS_FILE = BASE_DIR / "ideas.json"
OUTPUT_DIR = BASE_DIR / "output"
try:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
except OSError:
    pass

# Ideen-Quelle: "trends" = nur Google Trends (Standard, keine ideas.json) | "trends_then_file" = Trends, dann Fallback ideas.json | "file" = nur ideas.json
IDEA_SOURCE = os.getenv("IDEA_SOURCE", "trends")
TRENDS_COUNTRY = os.getenv("TRENDS_COUNTRY", "germany")
TRENDS_CACHE_HOURS = int(os.getenv("TRENDS_CACHE_HOURS", "12"))

# TikTok
TIKTOK_CLIENT_KEY = os.getenv("TIKTOK_CLIENT_KEY", "")
TIKTOK_CLIENT_SECRET = os.getenv("TIKTOK_CLIENT_SECRET", "")
TIKTOK_REDIRECT_URI = os.getenv("TIKTOK_REDIRECT_URI", "")
TIKTOK_ACCESS_TOKEN = os.getenv("TIKTOK_ACCESS_TOKEN", "")
TIKTOK_REFRESH_TOKEN = os.getenv("TIKTOK_REFRESH_TOKEN", "")

# Pexels (für Hintergrund-Videos und optional Bilder)
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")
# Suchbegriff für Hintergrund-Videos (z. B. "nature", "ocean", "forest")
VIDEO_BACKGROUND_QUERY = os.getenv("VIDEO_BACKGROUND_QUERY", "nature landscape")
# Optional: lokaler Ordner mit MP4/Clips als Hintergrund (relativer Pfad = ab Projektroot)
_bg_dir = (os.getenv("BACKGROUND_VIDEOS_DIR") or "").strip()
BACKGROUND_VIDEOS_DIR = (Path(_bg_dir).resolve() if os.path.isabs(_bg_dir) else (BASE_DIR / _bg_dir).resolve()) if _bg_dir else None

# TTS: Engine "edge" (kostenlos) oder "openai" (natürlicher, braucht OPENAI_API_KEY)
TTS_ENGINE = (os.getenv("TTS_ENGINE") or "edge").strip().lower()
# Edge-Stimme (de-DE-KatjaNeural …) oder OpenAI-Stimme (nova, alloy, echo, fable, onyx, shimmer)
TTS_VOICE = os.getenv("TTS_VOICE", "de-DE-KatjaNeural" if TTS_ENGINE != "openai" else "nova")
OPENAI_API_KEY = (os.getenv("OPENAI_API_KEY") or "").strip()

# Video-Einstellungen (auf dem Raspberry Pi optional kleiner für schnellere Encodes)
VIDEO_WIDTH = int(os.getenv("VIDEO_WIDTH", "1080"))
VIDEO_HEIGHT = int(os.getenv("VIDEO_HEIGHT", "1920"))
VIDEO_FPS = 30
VIDEO_DURATION_MIN = 3  # Sekunden
VIDEO_DURATION_MAX = 60  # TikTok max oft 3 Min, wir bleiben kürzer
