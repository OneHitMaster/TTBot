"""Erstellt TikTok-Videos: gute KI-Stimme (Edge TTS), synchroner Lauftext, Video- oder Gradient-Hintergrund."""
import os
import tempfile
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
        frame = _draw_text_frame(width, height, sent, font_size=60, margin=72, card_padding=40, card_radius=28)
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
        """Pexels oder lokaler Ordner – gibt Dateipfad zurück oder None (dann Gradient)."""
        if self.pexels_api_key:
            path = background_video.fetch_pexels_video(
                self.pexels_api_key,
                query=self.background_query or None,
                orientation="portrait",
            )
            if path:
                return path
        if self.background_videos_dir and self.background_videos_dir.is_dir():
            return background_video.get_local_background_video(self.background_videos_dir)
        return None

    def create(self, idea: Idea, output_filename: Optional[str] = None) -> str:
        """
        Erstellt ein Video: KI-Stimme, synchroner Lauftext, Hintergrund = Video (Natur etc.) oder Gradient.
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

        # 2. Hintergrund: Video (Pexels/lokal) oder Gradient
        bg_video_path = self._get_background_video_path(idea)
        temp_video_path = None
        layers = []

        if bg_video_path:
            try:
                bg_clip = _make_background_video_clip(
                    bg_video_path, self.width, self.height, total_duration
                )
                layers.append(bg_clip)
                dark = _make_dark_overlay(self.width, self.height, total_duration, opacity=0.42)
                layers.append(dark)
                if bg_video_path.startswith(tempfile.gettempdir()):
                    temp_video_path = bg_video_path
            except Exception:
                bg_video_path = None
                if layers:
                    for c in layers:
                        c.close()
                    layers = []

        if not layers:
            bg_img, clips_info = _timing_clips_from_frames(
                self.width, self.height, timings, total_duration, _GRADIENTS
            )
            bg_path = self.output_dir / f"bg_{idea_id}.png"
            bg_img.save(str(bg_path))
            bg_clip = ImageClip(str(bg_path))
            bg_clip = bg_clip.with_duration(total_duration) if _MOVIEPY_V2 else bg_clip.set_duration(total_duration)
            layers.append(bg_clip)

        # Text-Frames (clips_info nur wenn wir Gradient genutzt haben)
        if not bg_video_path:
            _, clips_info = _timing_clips_from_frames(
                self.width, self.height, timings, total_duration, _GRADIENTS
            )
        else:
            clips_info = []
            for sent, start, duration in timings:
                frame = _draw_text_frame(
                    self.width, self.height, sent, font_size=60, margin=72, card_padding=40, card_radius=28
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
        bg_path = self.output_dir / f"bg_{idea_id}.png"
        if os.path.exists(str(bg_path)):
            try:
                os.remove(str(bg_path))
            except OSError:
                pass

        return str(out_path)
