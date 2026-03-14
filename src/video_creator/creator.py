"""Erstellt TikTok-Videos: gute KI-Stimme (Edge TTS), synchroner Lauftext, Video- oder Gradient-Hintergrund."""
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont
try:
    from moviepy import ImageClip, AudioFileClip, ColorClip, CompositeVideoClip, VideoFileClip
    _MOVIEPY_V2 = True
except ImportError:
    from moviepy.editor import ImageClip, AudioFileClip, ColorClip, CompositeVideoClip, VideoFileClip
    _MOVIEPY_V2 = False

from src.ideas import Idea
from src.video_creator.tts_sync import create_audio_with_timing
from src.video_creator import background_video

# TikTok-Vertikalformat
WIDTH = 1080
HEIGHT = 1920

# Kräftige, sichtbare Verläufe – nicht mehr wie eine Einheitsfarbe
_GRADIENTS = [
    [(0x0d, 0x1b, 0x2d), (0x1b, 0x3a, 0x5c), (0x41, 0x6d, 0x9e)],   # Dunkel → Hellblau
    [(0x1a, 0x0a, 0x2e), (0x3d, 0x1e, 0x6d), (0x6b, 0x3a, 0x9a)],   # Tiefes Lila → Violett
    [(0x0f, 0x34, 0x60), (0x1e, 0x5a, 0x8c), (0x2e, 0x8b, 0xaa)],   # Navy → Türkis
    [(0x16, 0x21, 0x3e), (0x2d, 0x3d, 0x6b), (0x5c, 0x6d, 0x9e)],   # Blau-Slate
    [(0x2d, 0x1b, 0x4e), (0x5e, 0x3a, 0x8e), (0x7b, 0x5c, 0xb0)],   # Lila → Hell
    [(0x0a, 0x25, 0x3a), (0x1a, 0x4a, 0x6a), (0x3a, 0x7a, 0x9a)],   # Ozean hell
    [(0x1e, 0x12, 0x38), (0x3d, 0x2a, 0x5e), (0x6e, 0x5a, 0x9e)],   # Dunkelviolett → Lavendel
]

# Schriftarten (priorisiert: fette/lesbare)
_FONT_PATHS = [
    os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts", "arialbd.ttf"),
    os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts", "arial.ttf"),
    "arialbd.ttf",
    "arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.otf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]


def _get_font(size: int = 72):
    for path in _FONT_PATHS:
        if path and os.path.isfile(path):
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default()


def _make_gradient_image(width: int, height: int, gradient: List[Tuple[int, int, int]]) -> Image.Image:
    """Vertikaler + leichter diagonaler Verlauf, damit es nicht flach wirkt."""
    img = Image.new("RGB", (width, height))
    pix = img.load()
    n = len(gradient) - 1
    cx, cy = width / 2, height / 2
    max_dist = (cx * cx + cy * cy) ** 0.5
    for y in range(height):
        t = y / (height - 1) if height > 1 else 0
        for x in range(width):
            # Vertikal + leichter Diagonaleinfluss (von oben-links)
            t2 = t + 0.08 * (x / width - 0.5)
            t2 = max(0.0, min(1.0, t2))
            i = min(int(t2 * n), n - 1)
            local = (t2 * n) - i
            r = int(gradient[i][0] + (gradient[i + 1][0] - gradient[i][0]) * local)
            g = int(gradient[i][1] + (gradient[i + 1][1] - gradient[i][1]) * local)
            b = int(gradient[i][2] + (gradient[i + 1][2] - gradient[i][2]) * local)
            dist = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
            vignette = 1.0 - 0.15 * (dist / max_dist) ** 1.0
            r = max(0, min(255, int(r * vignette)))
            g = max(0, min(255, int(g * vignette)))
            b = max(0, min(255, int(b * vignette)))
            pix[x, y] = (r, g, b)
    return img


def _draw_text_frame(
    width: int,
    height: int,
    text: str,
    font_size: int = 68,
    margin: int = 80,
    card_padding: int = 0,
    card_radius: int = 0,
) -> Image.Image:
    """Moderner Lauftext ohne Box: weißer Text mit dezentem Rand für Lesbarkeit auf Video."""
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = _get_font(font_size)
    max_w = width - 2 * margin
    words = text.split()
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
    line_height = int(font_size * 1.45)
    total_h = len(lines) * line_height
    y0 = (height - total_h) // 2

    # Keine Box – nur Text mit Outline (Rand) für Lesbarkeit auf jedem Hintergrund
    outline_offsets = [(-2, -2), (-2, 0), (-2, 2), (0, -2), (0, 2), (2, -2), (2, 0), (2, 2)]
    outline_color = (0, 0, 0, 200)
    text_color = (255, 255, 255, 255)
    # Optional: leichter Schatten für Tiefe
    shadow_offset = (3, 4)
    shadow_color = (0, 0, 0, 140)

    for i, ln in enumerate(lines):
        bbox = draw.textbbox((0, 0), ln, font=font)
        tw = bbox[2] - bbox[0]
        x = (width - tw) // 2
        y = y0 + i * line_height
        # Schatten
        draw.text((x + shadow_offset[0], y + shadow_offset[1]), ln, font=font, fill=shadow_color)
        # Outline
        for dx, dy in outline_offsets:
            draw.text((x + dx, y + dy), ln, font=font, fill=outline_color)
        # Text
        draw.text((x, y), ln, font=font, fill=text_color)
    return img


def _make_background_video_clip(
    video_path: str,
    width: int,
    height: int,
    duration: float,
) -> "VideoFileClip":
    """Lädt ein Video, passt es auf width x height an (füllt Frame, Center-Crop) und Länge (Loop/Trim)."""
    clip = VideoFileClip(video_path)
    w, h = clip.w, clip.h
    if w <= 0 or h <= 0:
        clip.close()
        raise ValueError("Invalid video dimensions")
    scale = max(width / w, height / h)
    new_w, new_h = int(round(w * scale)), int(round(h * scale))
    try:
        if _MOVIEPY_V2:
            clip = clip.resized((new_w, new_h))
        else:
            clip = clip.resize((new_w, new_h))
    except Exception:
        if _MOVIEPY_V2:
            clip = clip.resized(height=height)
        else:
            clip = clip.resize(height=height)
        new_w, new_h = clip.w, clip.h
    # Center-Crop auf width x height
    x1 = max(0, (clip.w - width) // 2)
    y1 = max(0, (clip.h - height) // 2)
    if _MOVIEPY_V2:
        clip = clip.cropped(x1=x1, y1=y1, width=width, height=height)
    else:
        clip = clip.crop(x1=x1, y1=y1, width=width, height=height)
    # Länge anpassen: loopen oder kürzen
    if clip.duration >= duration:
        if _MOVIEPY_V2:
            clip = clip.subclipped(0, duration)
        else:
            clip = clip.subclip(0, duration)
    else:
        n = int(duration / clip.duration) + 1
        try:
            if _MOVIEPY_V2:
                from moviepy import concatenate_videoclips
            else:
                from moviepy.editor import concatenate_videoclips
            clips = [clip] * n
            clip = concatenate_videoclips(clips)
            if _MOVIEPY_V2:
                clip = clip.subclipped(0, duration)
            else:
                clip = clip.subclip(0, duration)
        except Exception:
            if _MOVIEPY_V2:
                clip = clip.subclipped(0, min(clip.duration, duration))
            else:
                clip = clip.subclip(0, min(clip.duration, duration))
    clip = clip.with_duration(duration) if _MOVIEPY_V2 else clip.set_duration(duration)
    return clip


def _make_dark_overlay(width: int, height: int, duration: float, opacity: float = 0.45):
    """Halbtransparenter dunkler Overlay damit Text auf Video gut lesbar bleibt."""
    overlay = ColorClip(size=(width, height), color=(0, 0, 0))
    overlay = overlay.with_duration(duration) if _MOVIEPY_V2 else overlay.set_duration(duration)
    overlay = overlay.with_opacity(opacity) if _MOVIEPY_V2 else overlay.set_opacity(opacity)
    return overlay


def _timing_clips_from_frames(
    width: int,
    height: int,
    timings: List[Tuple[str, float, float]],
    total_duration: float,
    gradient_colors: List,
) -> Tuple[Image.Image, List]:
    """Hintergrund-Bild + Liste (start, duration, PIL-Image) pro Satz."""
    import random
    bg_img = _make_gradient_image(width, height, random.choice(gradient_colors))
    clips_info = []
    for sent, start, duration in timings:
        frame = _draw_text_frame(width, height, sent, font_size=64, margin=72)
        clips_info.append((start, duration, frame))
    return bg_img, clips_info


class VideoCreator:
    """Erstellt Kurzvideos: Edge TTS, synchroner Lauftext, Video- oder Gradient-Hintergrund."""

    def __init__(
        self,
        output_dir: Path,
        width: int = WIDTH,
        height: int = HEIGHT,
        voice: str = "de-DE-KatjaNeural",
        pexels_api_key: str = "",
        background_query: str = "",
        background_videos_dir: Optional[Path] = None,
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.width = width
        self.height = height
        self.voice = voice or "de-DE-KatjaNeural"
        self.pexels_api_key = (pexels_api_key or "").strip()
        self.background_query = (background_query or "nature landscape").strip()
        self.background_videos_dir = Path(background_videos_dir) if background_videos_dir else None

    def _get_background_video_path(self, idea: Idea) -> Optional[str]:
        """Pexels oder lokaler Ordner – gibt Dateipfad zurück oder None."""
        query = (getattr(idea, "topic", None) or "").strip() or self.background_query or None
        if self.pexels_api_key:
            path = background_video.fetch_pexels_video(
                self.pexels_api_key,
                query=query,
                orientation="portrait",
            )
            if path:
                return path
        if self.background_videos_dir and self.background_videos_dir.is_dir():
            return background_video.get_local_background_video(self.background_videos_dir)
        return None

    def create(self, idea: Idea, output_filename: Optional[str] = None) -> str:
        """
        Erstellt ein Video nur mit Hintergrund-Video (Pexels oder lokaler Ordner).
        Ohne verfügbares Video wird der Prozess abgebrochen.
        """
        # Zuerst: Hintergrund-Video besorgen – sonst sofort abbrechen
        bg_video_path = self._get_background_video_path(idea)
        if not bg_video_path:
            raise RuntimeError(
                "Kein Hintergrund-Video verfügbar. "
                "PEXELS_API_KEY in .env setzen und gültig halten oder BACKGROUND_VIDEOS_DIR mit MP4-Dateien füllen. "
                "Prozess abgebrochen."
            )
        temp_video_path = bg_video_path if bg_video_path.startswith(tempfile.gettempdir()) else None

        idea_id = idea.id.replace("/", "_").replace(" ", "_")[:30]
        if output_filename:
            out_name = output_filename
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            out_name = f"video_{idea_id}_{timestamp}.mp4"
        out_path = self.output_dir / out_name
        audio_path = self.output_dir / f"audio_{idea_id}.mp3"
        full_text = (idea.title.strip() + ". " + idea.text.strip()) if idea.title else idea.text

        # 1. Audio + Satz-Timings (Edge TTS) – Zahlen/Erstens/Zweitens werden vor dem Vorlesen entfernt
        timings = create_audio_with_timing(
            full_text,
            voice=self.voice,
            output_audio_path=str(audio_path),
            lang="de",
        )
        audio = AudioFileClip(str(audio_path))
        total_duration = audio.duration

        # 2. Hintergrund-Video (bereits geprüft)
        try:
            bg_clip = _make_background_video_clip(
                bg_video_path, self.width, self.height, total_duration
            )
        except Exception as e:
            if temp_video_path and os.path.exists(temp_video_path):
                try:
                    os.remove(temp_video_path)
                except OSError:
                    pass
            raise RuntimeError(f"Hintergrund-Video konnte nicht geladen werden: {e}") from e
        if getattr(bg_clip, "duration", 0) <= 0:
            bg_clip.close()
            if temp_video_path and os.path.exists(temp_video_path):
                try:
                    os.remove(temp_video_path)
                except OSError:
                    pass
            raise RuntimeError("Hintergrund-Video hat keine gültige Dauer (Datei defekt?).")

        dark = _make_dark_overlay(self.width, self.height, total_duration, opacity=0.42)
        layers = [bg_clip, dark]
        quelle = "Pexels" if temp_video_path else "lokal"
        print(f"Hintergrund: Video-Clip wird verwendet ({quelle}).")
        print(f"  → Dieses Video öffnen: {out_name}")

        # Text-Frames (synced mit TTS)
        clips_info = []
        for sent, start, duration in timings:
            frame = _draw_text_frame(
                self.width, self.height, sent, font_size=64, margin=72
            )
            clips_info.append((start, duration, frame))

        overlay_clips = []
        for start, duration, pil_image in clips_info:
            tmp_path = self.output_dir / f"txt_{idea_id}_{start:.1f}.png"
            pil_image.save(str(tmp_path))
            clip = ImageClip(str(tmp_path))
            clip = clip.with_duration(duration) if _MOVIEPY_V2 else clip.set_duration(duration)
            clip = clip.with_start(start) if _MOVIEPY_V2 else clip.set_start(start)
            overlay_clips.append(clip)
            try:
                os.remove(str(tmp_path))
            except OSError:
                pass

        if _MOVIEPY_V2:
            video = CompositeVideoClip(layers + overlay_clips)
            video = video.with_audio(audio)
        else:
            video = CompositeVideoClip(layers + overlay_clips)
            video = video.set_audio(audio)

        video.write_videofile(
            str(out_path),
            fps=24,
            codec="libx264",
            audio_codec="aac",
            temp_audiofile=tempfile.mktemp(suffix=".m4a"),
            remove_temp=True,
            logger=None,
        )

        audio.close()
        video.close()
        for c in layers + overlay_clips:
            c.close()
        if temp_video_path and os.path.exists(temp_video_path):
            try:
                os.remove(temp_video_path)
            except OSError:
                pass
        for p in (str(audio_path),):
            if os.path.exists(p):
                try:
                    os.remove(p)
                except OSError:
                    pass

        return str(out_path)
