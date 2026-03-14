"""Konfiguration aus Umgebungsvariablen."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Pfade
BASE_DIR = Path(__file__).resolve().parent
IDEAS_FILE = BASE_DIR / "ideas.json"
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# Ideen-Quelle: "file" = nur ideas.json | "trends" = nur Google Trends | "trends_then_file" = zuerst Trends, dann Datei
IDEA_SOURCE = os.getenv("IDEA_SOURCE", "trends_then_file")
TRENDS_COUNTRY = os.getenv("TRENDS_COUNTRY", "germany")
TRENDS_CACHE_HOURS = int(os.getenv("TRENDS_CACHE_HOURS", "12"))

# TikTok
TIKTOK_CLIENT_KEY = os.getenv("TIKTOK_CLIENT_KEY", "")
TIKTOK_CLIENT_SECRET = os.getenv("TIKTOK_CLIENT_SECRET", "")
TIKTOK_REDIRECT_URI = os.getenv("TIKTOK_REDIRECT_URI", "")
TIKTOK_ACCESS_TOKEN = os.getenv("TIKTOK_ACCESS_TOKEN", "")
TIKTOK_REFRESH_TOKEN = os.getenv("TIKTOK_REFRESH_TOKEN", "")

# Optional: Pexels für Bilder
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")

# TTS: Edge-Stimme (z. B. de-DE-KatjaNeural, de-DE-ConradNeural)
TTS_VOICE = os.getenv("TTS_VOICE", "de-DE-KatjaNeural")

# Video-Einstellungen (auf dem Raspberry Pi optional kleiner für schnellere Encodes)
VIDEO_WIDTH = int(os.getenv("VIDEO_WIDTH", "1080"))
VIDEO_HEIGHT = int(os.getenv("VIDEO_HEIGHT", "1920"))
VIDEO_FPS = 30
VIDEO_DURATION_MIN = 3  # Sekunden
VIDEO_DURATION_MAX = 60  # TikTok max oft 3 Min, wir bleiben kürzer
