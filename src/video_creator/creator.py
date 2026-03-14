"""Erstellt TikTok-Videos aus Ideen: TTS + Bild/Clip."""
import os
import tempfile
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont
from gtts import gTTS
try:
    from moviepy import ImageClip, AudioFileClip, ColorClip
    _MOVIEPY_V2 = True
except ImportError:
    from moviepy.editor import ImageClip, AudioFileClip, ColorClip
    _MOVIEPY_V2 = False

from src.ideas import Idea

# TikTok-Vertikalformat
WIDTH = 1080
HEIGHT = 1920

# Schriftarten pro Plattform (Windows, Linux/Raspberry Pi)
_FONT_PATHS = [
    "arial.ttf",
    os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts", "arial.ttf"),
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
]


def _get_font(size: int = 72):
    """Lädt eine verfügbare Schriftart (Windows, Linux, Raspberry Pi)."""
    for path in _FONT_PATHS:
        if path and os.path.isfile(path):
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default()


def _draw_title_on_image(width: int, height: int, title: str, path: str) -> None:
    """Zeichnet Titel auf ein Bild (ohne ImageMagick)."""
    img = Image.new("RGB", (width, height), color=(40, 40, 60))
    draw = ImageDraw.Draw(img)
    font = _get_font(72)
    # Text zentrieren (einfache Umbrüche bei zu langen Zeilen)
    margin = 80
    max_w = width - 2 * margin
    words = title.split()
    lines = []
    line = []
    for w in words:
        line.append(w)
        bbox = draw.textbbox((0, 0), " ".join(line), font=font)
        if bbox[2] - bbox[0] > max_w and len(line) > 1:
            line.pop()
            lines.append(" ".join(line))
            line = [w]
    if line:
        lines.append(" ".join(line))
    y = (height - len(lines) * 80) // 2
    for ln in lines:
        bbox = draw.textbbox((0, 0), ln, font=font)
        tw = bbox[2] - bbox[0]
        x = (width - tw) // 2
        draw.text((x, y), ln, fill="white", font=font)
        y += 80
    img.save(path)


class VideoCreator:
    """Erstellt ein Kurzvideo aus einer Idea (Text-to-Speech + visueller Inhalt)."""

    def __init__(
        self,
        output_dir: Path,
        width: int = WIDTH,
        height: int = HEIGHT,
        lang: str = "de",
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.width = width
        self.height = height
        self.lang = lang

    def _create_audio(self, text: str, idea_id: str) -> str:
        """Erstellt Audio-Datei mit gTTS."""
        tts = gTTS(text=text, lang=self.lang, slow=False)
        path = self.output_dir / f"audio_{idea_id}.mp3"
        tts.save(str(path))
        return str(path)

    def create(self, idea: Idea, output_filename: Optional[str] = None) -> str:
        """
        Erstellt ein Video aus der Idee.
        - Spricht den Text per gTTS
        - Zeigt Hintergrund mit Titel (PIL, kein ImageMagick nötig)
        - Länge = Audiolänge
        Gibt den Pfad zur erstellten MP4-Datei zurück.
        """
        idea_id = idea.id.replace("/", "_").replace(" ", "_")
        out_name = output_filename or f"video_{idea_id}.mp4"
        out_path = self.output_dir / out_name

        # 1. Audio aus Text
        audio_path = self._create_audio(idea.text, idea_id)
        audio = AudioFileClip(audio_path)
        duration = audio.duration

        # 2. Hintergrundbild mit Titel (PIL)
        frame_path = self.output_dir / f"frame_{idea_id}.png"
        _draw_title_on_image(self.width, self.height, idea.title, str(frame_path))
        bg = ImageClip(str(frame_path))
        bg = bg.with_duration(duration) if _MOVIEPY_V2 else bg.set_duration(duration)

        # 3. Audio anhängen
        video = bg.with_audio(audio) if _MOVIEPY_V2 else bg.set_audio(audio)

        # 4. Schreiben (MP4, H.264 für TikTok)
        video.write_videofile(
            str(out_path),
            fps=24,
            codec="libx264",
            audio_codec="aac",
            temp_audiofile=tempfile.mktemp(suffix=".m4a"),
            remove_temp=True,
            logger=None,
        )

        # Aufräumen
        audio.close()
        video.close()
        for p in (audio_path, str(frame_path)):
            if p and os.path.exists(p):
                try:
                    os.remove(p)
                except OSError:
                    pass

        return str(out_path)
