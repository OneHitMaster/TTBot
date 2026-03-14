"""Ideensammlung: Lädt Ideen aus Dateien oder kann später um APIs erweitert werden."""
import json
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

    def caption(self, max_length: int = 2200) -> str:
        """Caption für TikTok (max 2200 Zeichen)."""
        hashtag_str = " ".join(self.hashtags)
        caption = f"{self.title}\n\n{self.text}\n\n{hashtag_str}"
        return caption[:max_length] if len(caption) > max_length else caption


class IdeaCollector:
    """Sammelt und verwaltet Video-Ideen."""

    def __init__(self, ideas_path: Optional[Path] = None):
        self.ideas_path = ideas_path or Path(__file__).resolve().parent.parent.parent / "ideas.json"
        self._used_ids: set = set()

    def load_ideas(self) -> List[Idea]:
        """Lädt alle Ideen aus der JSON-Datei."""
        if not self.ideas_path.exists():
            return []
        with open(self.ideas_path, encoding="utf-8") as f:
            data = json.load(f)
        return [
            Idea(
                id=item.get("id", str(i)),
                title=item.get("title", ""),
                text=item.get("text", ""),
                hashtags=item.get("hashtags", []),
            )
            for i, item in enumerate(data)
        ]

    def get_next_idea(self) -> Optional[Idea]:
        """Gibt die nächste noch nicht verwendete Idee zurück."""
        ideas = self.load_ideas()
        for idea in ideas:
            if idea.id not in self._used_ids:
                return idea
        return None

    def mark_used(self, idea: Idea) -> None:
        """Markiert eine Idee als verwendet (wird in dieser Session nicht erneut gewählt)."""
        self._used_ids.add(idea.id)
