"""Hintergrund-Videos: Pexels API – themenbezogen oder Natur – oder lokaler Ordner."""
import os
import random
import tempfile
import urllib.request
from pathlib import Path
from typing import List, Optional

# Deutsche Themen → englische Pexels-Suchbegriffe (themenpassende Clips)
TOPIC_TO_PEXELS_QUERY = {
    "geld": "money finance success",
    "gewohnheiten": "habits routine morning",
    "psychologie": "psychology mind thinking",
    "produktivität": "productivity work focus",
    "motivation": "motivation success drive",
    "schlaf": "sleep rest bedroom",
    "gesundheit": "health fitness wellness",
    "sparen": "money savings",
    "morgen": "sunrise morning nature",
    "stress": "relax nature calm",
    "lernen": "study learning books",
    "sport": "sports fitness workout",
    "ernährung": "healthy food nutrition",
    "selbstdisziplin": "discipline focus success",
    "prokrastination": "work laptop focus",
    "routine": "morning routine habits",
    "morgenroutine": "morning routine sunrise",
    "finanzen": "money finance",
    "mindset": "mindset success",
    "entspannung": "relax calm nature",
    "arbeit": "work office productivity",
    "bücher": "books reading",
    "träume": "dreams sky clouds",
    "gehirn": "brain mind thinking",
    "zeit": "time clock minimal",
    "gedächtnis": "memory brain",
    "wissen": "knowledge books",
    "mensch": "human nature",
    "entscheidungen": "decision thinking",
}

# Fallback: allgemeine, stimmungsvolle Clips
DEFAULT_QUERIES = [
    "nature landscape",
    "forest trees",
    "ocean waves",
    "mountains",
    "sunset",
    "waterfall",
    "sky clouds",
    "beach",
    "minimal calm",
]


def _topic_to_pexels_query(topic: str) -> str:
    """Macht aus einem deutschen Thema eine passende Pexels-Suche (englisch für bessere Treffer)."""
    if not topic or not topic.strip():
        return ""
    t = topic.strip().lower()
    # Exakter Treffer
    if t in TOPIC_TO_PEXELS_QUERY:
        return TOPIC_TO_PEXELS_QUERY[t]
    # Einzelwörter prüfen (z. B. "Geld und Sparen" -> money)
    for key, query in TOPIC_TO_PEXELS_QUERY.items():
        if key in t or t in key:
            return query
    # Thema als Suchbegriff (Pexels versteht auch deutsche Begriffe, aber Englisch liefert mehr)
    return t.replace(" ", " ")


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


def _search_and_download(api_key: str, q: str, orientation: Optional[str], per_page: int) -> Optional[str]:
    """Hilfe: eine Pexels-Suche durchführen und ein Video herunterladen."""
    import json
    url = (
        "https://api.pexels.com/v1/videos/search"
        f"?query={urllib.request.quote(q)}"
        f"&per_page={per_page}"
    )
    if orientation:
        url += f"&orientation={orientation}"
    try:
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": api_key.strip(),
                "User-Agent": "TTBot/1.0 (https://github.com)",
            },
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read().decode()
    except Exception as e:
        if os.environ.get("TTBOT_DEBUG"):
            print(f"[Pexels] Suche fehlgeschlagen: {e}")
        return None
    try:
        out = json.loads(data)
        videos = out.get("videos") or []
        if not videos:
            return None
        video = random.choice(videos)
        files = video.get("video_files") or []
        # Irgendein File mit Link nehmen; bevorzuge mind. 720p (Höhe) oder beste Qualität
        best = None
        for f in files:
            link = f.get("link")
            if not link:
                continue
            h = f.get("height") or 0
            if best is None or (best.get("height") or 0) < h:
                best = f
        if not best:
            return None
        download_url = best.get("link")
        if not download_url:
            return None
        tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
        tmp.close()
        downloaded = _download_url(download_url, tmp.name)
        if not downloaded:
            import time
            time.sleep(1)
            downloaded = _download_url(download_url, tmp.name)
        if not downloaded:
            if os.environ.get("TTBOT_DEBUG"):
                print("[Pexels] Download der Video-URL fehlgeschlagen (nach 2 Versuchen).")
            try:
                os.remove(tmp.name)
            except OSError:
                pass
            return None
        # Nur gültige Dateien zurückgeben (nicht leer)
        try:
            if os.path.getsize(tmp.name) < 1000:
                if os.environ.get("TTBOT_DEBUG"):
                    print("[Pexels] Heruntergeladene Datei zu klein oder leer.")
                os.remove(tmp.name)
                return None
        except OSError:
            return None
        return tmp.name
    except Exception as e:
        if os.environ.get("TTBOT_DEBUG"):
            print(f"[Pexels] Verarbeitung fehlgeschlagen: {e}")
        return None


def fetch_pexels_video(
    api_key: str,
    query: Optional[str] = None,
    orientation: str = "portrait",
    per_page: int = 20,
) -> Optional[str]:
    """
    Sucht ein themenpassendes Video bei Pexels. query = Ideen-Thema (z. B. aus idea.topic).
    Deutsche Themen werden für bessere Treffer auf englische Suchbegriffe gemappt.
    """
    if not api_key or not api_key.strip():
        return None
    raw = (query or "").strip()
    q = _topic_to_pexels_query(raw) if raw else ""
    if not q:
        q = random.choice(DEFAULT_QUERIES)
    # Zuerst mit Portrait, dann ohne Orientierung (mehr Treffer)
    path = _search_and_download(api_key, q, "portrait", per_page)
    if path:
        return path
    path = _search_and_download(api_key, q, None, per_page)
    return path


def get_local_background_video(folder: Path) -> Optional[str]:
    """Wählt zufällig ein Video aus einem lokalen Ordner (z. B. output/backgrounds)."""
    if not folder or not folder.is_dir():
        return None
    exts = {".mp4", ".mov", ".webm", ".mkv"}
    files = [f for f in folder.iterdir() if f.is_file() and f.suffix.lower() in exts]
    if not files:
        return None
    return str(random.choice(files))
