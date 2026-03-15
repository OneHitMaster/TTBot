"""Ideen aus aktuellen Trends (Google Trends). Kein manuelles Eintragen nötig."""
import json
import re
import random
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional

from src.ideas.collector import Idea

# Google Trends – Land für Trends (pn: p15 = Deutschland)
TRENDS_COUNTRY_MAP = {
    "germany": "p15",
    "de": "p15",
    "austria": "p44",
    "at": "p44",
    "switzerland": "p46",
    "ch": "p46",
    "usa": "p1",
    "us": "p1",
    "united_states": "p1",
}

# Titel: Fakten / „Das weißt du nicht“ – keine Koch- oder Rezept-Themen
TREND_TITLE_TEMPLATES = [
    "Fakten über {topic}, die kaum einer kennt",
    "Was du über {topic} noch nicht wusstest",
    "5 Fakten zu {topic}, die dich überraschen",
    "Über {topic}: Das haben dir die wenigsten erzählt",
    "Wahre Fakten über {topic} – kein Bullshit",
    "Das solltest du über {topic} wissen",
    "Überraschende Fakten über {topic}",
    "Was wirklich hinter {topic} steckt – Fakten statt Mythen",
]

# Gesprochener Text: Fakten, Wissenswertes, keine Rezepte
TREND_TEXT_TEMPLATES = [
    "Die wenigsten kennen diese Fakten zu {topic}. Hier die Punkte, die wirklich hängen bleiben.",
    "Über {topic} kursieren viele Mythen. Das sind die Fakten, die stimmen.",
    "Was du über {topic} noch nicht wusstest – kurz und mit Substanz.",
    "Drei Fakten zu {topic}, die dein Bild davon verändern können.",
    "Experten wissen es, die meisten nicht: So tickt {topic} wirklich.",
    "Über {topic}: Hier die Fakten, die kaum jemand kennt.",
    "Kurz und faktenbasiert: Das solltest du zu {topic} wissen.",
    "Was wirklich hinter {topic} steckt – ohne Floskeln, nur Fakten.",
]


def _hashtag_safe(s: str) -> str:
    """Macht einen String zu einem gültigen Hashtag (ohne Leerzeichen, Sonderzeichen)."""
    s = re.sub(r"[^\wäöüßÄÖÜ]", "", s)
    return s.lower()[:30] if s else "trend"


def fetch_trending_topics(country: str = "germany", max_topics: int = 15) -> List[str]:
    """Lädt aktuelle Suchtrends von Google Trends – Themen, die gerade viele bewegen und oft gut auf TikTok funktionieren."""
    try:
        from pytrends.request import TrendReq
    except ImportError:
        return []

    pn = TRENDS_COUNTRY_MAP.get(country.lower(), "p15")
    try:
        trend_req = TrendReq(hl="de", tz=360)
        df = trend_req.trending_searches(pn=pn)
        if df is None or df.empty:
            return []
        # DataFrame: erste Spalte auslesen (Trend-Begriffe)
        if hasattr(df, "iloc"):
            col = df.iloc[:, 0]
            topics = col.astype(str).str.strip().tolist()
        elif hasattr(df, "tolist"):
            topics = [str(x).strip() for x in df.tolist()]
        else:
            topics = [str(x).strip() for x in df]
        return [t for t in topics if len(t) > 1][:max_topics]
    except Exception:
        return []


def trends_to_ideas(
    topics: List[str],
    text_templates: Optional[List[str]] = None,
    title_templates: Optional[List[str]] = None,
) -> List[Idea]:
    """Wandelt Trend-Themen in Video-Ideen um – mit Hooks für mehr Likes und Follows."""
    text_tpl = text_templates or TREND_TEXT_TEMPLATES
    title_tpl = title_templates or TREND_TITLE_TEMPLATES
    ideas = []
    for i, topic in enumerate(topics):
        if not topic or len(topic) < 2:
            continue
        title = random.choice(title_tpl).format(topic=topic)
        text = random.choice(text_tpl).format(topic=topic)
        tag = _hashtag_safe(topic)
        # Hashtags für Reichweite: fyp/fürdich, viral, Thema, Learn
        hashtags = [f"#{tag}", "#fyp", "#fürdich", "#viral", "#learnontiktok", "#wissen"]
        ideas.append(
            Idea(
                id=f"trend_{i}_{tag}",
                title=title,
                text=text,
                hashtags=hashtags,
                topic=topic,
            )
        )
    return ideas


def get_cached_trends_path(base_dir: Path) -> Path:
    return base_dir / "output" / "trends_cache.json"


def load_cached_trend_ideas(base_dir: Path, max_age_hours: int = 12) -> Optional[List[Idea]]:
    """Lädt gecachte Trend-Ideen, wenn noch nicht abgelaufen."""
    path = get_cached_trends_path(base_dir)
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        cached_at = datetime.fromisoformat(data["cached_at"])
        if datetime.now() - cached_at > timedelta(hours=max_age_hours):
            return None
        return [Idea(**item) for item in data["ideas"]]
    except Exception:
        return None


def save_trend_ideas_cache(base_dir: Path, ideas: List[Idea]) -> None:
    """Speichert Trend-Ideen im Cache (JSON)."""
    path = get_cached_trends_path(base_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "cached_at": datetime.now().isoformat(),
        "ideas": [
            {"id": i.id, "title": i.title, "text": i.text, "hashtags": i.hashtags, "topic": getattr(i, "topic", None)}
            for i in ideas
        ],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
