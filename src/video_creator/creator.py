"""Erstellt TikTok-Videos: gute KI-Stimme (Edge TTS), synchroner Lauftext, ansprechender Look."""
import os
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont
try:
    from moviepy import ImageClip, AudioFileClip, ColorClip, CompositeVideoClip
    _MOVIEPY_V2 = True
except ImportError:
    from moviepy.editor import ImageClip, AudioFileClip, ColorClip, CompositeVideoClip
    _MOVIEPY_V2 = False

from src.ideas import Idea
from src.video_creator.tts_sync import create_audio_with_timing

# TikTok-Vertikalformat
WIDTH = 1080
HEIGHT = 1920

# Ansprechende Hintergründe – modern, einladend, gut lesbar
_GRADIENTS = [
    [(0x1a, 0x1a, 0x2e), (0x16, 0x21, 0x3e), (0x0f, 0x34, 0x60)],   # Navy (vertrauenswürdig)
    [(0x0f, 0x0c, 0x29), (0x30, 0x2b, 0x63), (0x24, 0x24, 0x42)],   # Dunkelblau–Lila
    [(0x2d, 0x1b, 0x4e), (0x1a, 0x0a, 0x2a), (0x16, 0x0e, 0x28)],   # Tiefes Lila
    [(0x1e, 0x3a, 0x5c), (0x14, 0x2e, 0x4a), (0x0d, 0x21, 0x36)],   # Ozean
    [(0x33, 0x24, 0x4d), (0x24, 0x18, 0x3a), (0x1a, 0x12, 0x2e)],   # Weiches Lila
    [(0x1b, 0x26, 0x38), (0x25, 0x32, 0x48), (0x14, 0x1e, 0x2d)],   # Slate
    [(0x20, 0x2a, 0x3a), (0x2c, 0x3d, 0x52), (0x1a, 0x28, 0x38)],   # Kühles Grau-Blau
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
    """Vertikaler Farbverlauf mit weicher Vignette – Fokus in der Mitte."""
    img = Image.new("RGB", (width, height))
    pix = img.load()
    n = len(gradient) - 1
    cx, cy = width / 2, height / 2
    max_dist = (cx * cx + cy * cy) ** 0.5
    for y in range(height):
        t = y / (height - 1) if height > 1 else 0
        i = min(int(t * n), n - 1)
        local = (t * n) - i
        r = int(gradient[i][0] + (gradient[i + 1][0] - gradient[i][0]) * local)
        g = int(gradient[i][1] + (gradient[i + 1][1] - gradient[i][1]) * local)
        b = int(gradient[i][2] + (gradient[i + 1][2] - gradient[i][2]) * local)
        for x in range(width):
            dist = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
            vignette = 1.0 - 0.12 * (dist / max_dist) ** 1.2  # Rand leicht abdunkeln
            r2 = max(0, min(255, int(r * vignette)))
            g2 = max(0, min(255, int(g * vignette)))
            b2 = max(0, min(255, int(b * vignette)))
            pix[x, y] = (r2, g2, b2)
    return img


def _draw_text_frame(
    width: int,
    height: int,
    text: str,
    font_size: int = 62,
    margin: int = 90,
    card_padding: int = 44,
    card_radius: int = 32,
) -> Image.Image:
    """Zeichnet einen Satz in einer weichen Text-Karte – klar lesbar, modern (RGBA Overlay)."""
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = _get_font(font_size)
    max_w = width - 2 * margin - 2 * card_padding
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
    line_height = int(font_size * 1.38)
    total_h = len(lines) * line_height
    y0 = (height - total_h) // 2

    # Bounding-Box des gesamten Textblocks
    max_line_w = 0
    for ln in lines:
        bbox = draw.textbbox((0, 0), ln, font=font)
        max_line_w = max(max_line_w, bbox[2] - bbox[0])
    box_w = max_line_w + 2 * card_padding
    box_h = total_h + 2 * card_padding
    x1 = (width - box_w) // 2
    y1 = y0 - card_padding
    x2 = x1 + box_w
    y2 = y1 + box_h

    # Weiche Text-Karte (abgerundet, halbtransparent) – wirkt einladend
    if hasattr(draw, "rounded_rectangle"):
        draw.rounded_rectangle(
            [x1, y1, x2, y2],
            radius=card_radius,
            fill=(0, 0, 0, 200),
            outline=(255, 255, 255, 60),
            width=2,
        )
    else:
        draw.rectangle([x1, y1, x2, y2], fill=(0, 0, 0, 200), outline=(255, 255, 255, 80))

    # Text zentriert in der Karte (mit weichem Schatten)
    for i, ln in enumerate(lines):
        bbox = draw.textbbox((0, 0), ln, font=font)
        tw = bbox[2] - bbox[0]
        x = (width - tw) // 2
        y = y0 + i * line_height
        draw.text((x + 2, y + 2), ln, font=font, fill=(0, 0, 0, 140))
        draw.text((x, y), ln, font=font, fill=(255, 255, 255, 255))
    return img


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
        frame = _draw_text_frame(width, height, sent, font_size=60, margin=72, card_padding=40, card_radius=28)
        clips_info.append((start, duration, frame))
    return bg_img, clips_info


class VideoCreator:
    """Erstellt ansprechende Kurzvideos: Edge TTS, synchroner Lauftext, Gradient-Hintergrund."""

    def __init__(
        self,
        output_dir: Path,
        width: int = WIDTH,
        height: int = HEIGHT,
        voice: str = "de-DE-KatjaNeural",
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.width = width
        self.height = height
        self.voice = voice or "de-DE-KatjaNeural"

    def create(self, idea: Idea, output_filename: Optional[str] = None) -> str:
        """
        Erstellt ein Video: gute KI-Stimme, Text läuft synchron zum Gesprochenen, schöner Hintergrund.
        """
        idea_id = idea.id.replace("/", "_").replace(" ", "_")[:30]
        out_name = output_filename or f"video_{idea_id}.mp4"
        out_path = self.output_dir / out_name
        audio_path = self.output_dir / f"audio_{idea_id}.mp3"
        full_text = (idea.title.strip() + ". " + idea.text.strip()) if idea.title else idea.text

        # 1. Audio + Satz-Timings (Edge TTS)
        timings = create_audio_with_timing(
            full_text,
            voice=self.voice,
            output_audio_path=str(audio_path),
            lang="de",
        )
        audio = AudioFileClip(str(audio_path))
        total_duration = audio.duration

        # 2. Hintergrund (Gradient) + Text-Frames pro Satz
        bg_img, clips_info = _timing_clips_from_frames(
            self.width, self.height, timings, total_duration, _GRADIENTS
        )
        bg_path = self.output_dir / f"bg_{idea_id}.png"
        bg_img.save(str(bg_path))

        bg_clip = ImageClip(str(bg_path))
        bg_clip = bg_clip.with_duration(total_duration) if _MOVIEPY_V2 else bg_clip.set_duration(total_duration)

        # 3. Text-Overlays mit Start/Dauer
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
            video = CompositeVideoClip([bg_clip] + overlay_clips)
            video = video.with_audio(audio)
        else:
            video = CompositeVideoClip([bg_clip] + overlay_clips)
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
        bg_clip.close()
        for c in overlay_clips:
            c.close()
        for p in (str(audio_path), str(bg_path)):
            if os.path.exists(p):
                try:
                    os.remove(p)
                except OSError:
                    pass

        return str(out_path)
