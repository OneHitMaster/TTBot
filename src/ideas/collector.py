"""Ideensammlung: Standard = nur Google Trends (aktuelle Suchtrends, keine ideas.json nötig)."""
import json
import random
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Idea:
    """Eine einzelne Video-Idee."""
    id: str
    title: str
    text: str
    hashtags: List[str]
    topic: Optional[str] = None  # optional, z. B. für Pexels-Suche

    def caption(self, max_length: int = 2200) -> str:
        """Caption für TikTok (max 2200 Zeichen)."""
        hashtag_str = " ".join(self.hashtags)
        caption = f"{self.title}\n\n{self.text}\n\n{hashtag_str}"
        return caption[:max_length] if len(caption) > max_length else caption


class IdeaCollector:
    """Sammelt und verwaltet Video-Ideen (aus Datei und/oder aus Trends)."""

    def __init__(
        self,
        ideas_path: Optional[Path] = None,
        source: str = "trends",
        base_dir: Optional[Path] = None,
        trends_country: str = "germany",
        trends_cache_hours: int = 12,
    ):
        self.ideas_path = ideas_path or Path(__file__).resolve().parent.parent.parent / "ideas.json"
        self.source = source  # "trends" (Standard) | "trends_then_file" | "file"
        self.base_dir = base_dir or self.ideas_path.parent
        self.trends_country = trends_country
        self.trends_cache_hours = trends_cache_hours
        self._used_ids: set = set()
        self._trend_ideas: Optional[List[Idea]] = None

    def _get_trend_ideas(self) -> List[Idea]:
        """Lädt Trend-Ideen (Cache oder frisch von Google Trends)."""
        if self._trend_ideas is not None:
            return self._trend_ideas
        from src.ideas import trends
        cached = trends.load_cached_trend_ideas(self.base_dir, self.trends_cache_hours)
        if cached:
            self._trend_ideas = cached
            return self._trend_ideas
        topics = trends.fetch_trending_topics(country=self.trends_country, max_topics=15)
        if not topics:
            self._trend_ideas = []
            return []
        self._trend_ideas = trends.trends_to_ideas(topics)
        trends.save_trend_ideas_cache(self.base_dir, self._trend_ideas)
        return self._trend_ideas

    def load_ideas(self) -> List[Idea]:
        """Lädt alle Ideen aus der JSON-Datei. Ungültige Einträge werden übersprungen."""
        if not self.ideas_path.exists():
            return []
        try:
            with open(self.ideas_path, encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return []
        if not isinstance(data, list):
            return []
        ideas = []
        for i, item in enumerate(data):
            if not isinstance(item, dict):
                continue
            title = item.get("title") or ""
            text = item.get("text") or ""
            if not title and not text:
                continue
            ideas.append(
                Idea(
                    id=str(item.get("id", i)),
                    title=title,
                    text=text,
                    hashtags=item.get("hashtags") if isinstance(item.get("hashtags"), list) else [],
                    topic=item.get("topic"),
                )
            )
        return ideas

    def get_next_idea(self) -> Optional[Idea]:
        """Gibt eine zufällige, noch nicht verwendete Idee zurück (Trends und/oder Datei)."""
        candidates: List[Idea] = []
        if self.source in ("trends", "trends_then_file"):
            for idea in self._get_trend_ideas():
                if idea.id not in self._used_ids:
                    candidates.append(idea)
            if self.source == "trends" and not candidates:
                return None
        if not candidates:
            for idea in self.load_ideas():
                if idea.id not in self._used_ids:
                    candidates.append(idea)
        if not candidates:
            return None
        return random.choice(candidates)

    def mark_used(self, idea: Idea) -> None:
        """Markiert eine Idee als verwendet (wird in dieser Session nicht erneut gewählt)."""
        self._used_ids.add(idea.id)
