"""Hintergrund-Videos: Pexels API (Natur, etc.) oder lokaler Ordner."""
import os
import random
import tempfile
import urllib.request
from pathlib import Path
from typing import List, Optional

# Suchbegriffe für Abwechslung (Natur, Landschaft, entspannend)
DEFAULT_QUERIES = [
    "nature landscape",
    "forest trees",
    "ocean waves",
    "mountains",
    "sunset",
    "waterfall",
    "sky clouds",
    "beach",
]


def _download_url(url: str, path: str) -> bool:
    """Lädt eine URL in eine Datei."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "TTBot/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            with open(path, "wb") as f:
                f.write(resp.read())
        return True
    except Exception:
        return False


def fetch_pexels_video(
    api_key: str,
    query: Optional[str] = None,
    orientation: str = "portrait",
    per_page: int = 10,
) -> Optional[str]:
    """
    Sucht ein Video bei Pexels, lädt es herunter und gibt den lokalen Dateipfad zurück.
    Geeignet für vertikales TikTok-Format (orientation=portrait).
    """
    if not api_key or not api_key.strip():
        return None
    q = (query or random.choice(DEFAULT_QUERIES)).strip()
    url = (
        "https://api.pexels.com/v1/videos/search"
        f"?query={urllib.request.quote(q)}"
        f"&orientation={orientation}"
        f"&per_page={per_page}"
        "&size=medium"
    )
    try:
        req = urllib.request.Request(url, headers={"Authorization": api_key.strip()})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read().decode()
    except Exception:
        return None
    try:
        import json
        out = json.loads(data)
        videos = out.get("videos") or []
        if not videos:
            return None
        video = random.choice(videos)
        files = video.get("video_files") or []
        # Bevorzuge portrait (Höhe >= Breite) und akzeptable Qualität
        best = None
        for f in files:
            w = f.get("width") or 0
            h = f.get("height") or 0
            link = f.get("link")
            if not link:
                continue
            if h >= w and h >= 720:  # vertikal, mind. HD-Höhe
                if best is None or (best.get("height") or 0) < h:
                    best = f
        if best is None:
            best = files[0] if files else None
        if not best:
            return None
        download_url = best.get("link")
        if not download_url:
            return None
        ext = ".mp4"
        tmp = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
        tmp.close()
        if _download_url(download_url, tmp.name):
            return tmp.name
        try:
            os.remove(tmp.name)
        except OSError:
            pass
        return None
    except Exception:
        return None


def get_local_background_video(folder: Path) -> Optional[str]:
    """Wählt zufällig ein Video aus einem lokalen Ordner (z. B. output/backgrounds)."""
    if not folder or not folder.is_dir():
        return None
    exts = {".mp4", ".mov", ".webm", ".mkv"}
    files = [f for f in folder.iterdir() if f.is_file() and f.suffix.lower() in exts]
    if not files:
        return None
    return str(random.choice(files))
