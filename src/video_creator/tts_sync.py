"""High-Quality TTS (Edge) mit Satz-Timing für synchronen Lauftext."""
import asyncio
import os
import tempfile
from pathlib import Path
from typing import List, Tuple

# Edge TTS – deutsche Neural-Stimmen (klingen natürlich)
EDGE_VOICES_DE = [
    "de-DE-KatjaNeural",   # weiblich, klar
    "de-DE-ConradNeural",   # männlich, ruhig
    "de-DE-AmalaNeural",    # weiblich
    "de-DE-KillianNeural",  # männlich
]


def _split_sentences(text: str) -> List[str]:
    """Teilt Text in Sätze (für synchrone Anzeige)."""
    import re
    text = text.strip()
    if not text:
        return []
    # Bei . ! ? oder Zeilenumbruch trennen, Abkürzungen grob erhalten
    parts = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [p.strip() for p in parts if p.strip()]


async def _generate_segment_async(voice: str, text: str, path: str) -> None:
    """Erzeugt Audio für einen Satz (Datei unter path)."""
    import edge_tts
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(path)


def create_audio_with_timing(
    text: str,
    voice: str,
    output_audio_path: str,
    lang: str = "de",
) -> List[Tuple[str, float, float]]:
    """
    Erzeugt Audio mit Edge TTS und liefert Satz-Timings: [(satz, start_sec, duration_sec), ...].
    """
    try:
        import edge_tts
    except ImportError:
        # Fallback: gTTS, ein grober Block
        from gtts import gTTS
        tts = gTTS(text=text, lang=lang, slow=False)
        tts.save(output_audio_path)
        # Eine "Phrase" über die ganze Länge
        try:
            from moviepy.editor import AudioFileClip
            dur = AudioFileClip(output_audio_path).duration
        except Exception:
            dur = max(3.0, len(text) / 12.0)
        return [(text.strip(), 0.0, dur)]

    sentences = _split_sentences(text)
    if not sentences:
        sentences = [text[:500] or " "]

    # Stimme wählen (Deutsch)
    if not voice or voice == "auto":
        voice = "de-DE-KatjaNeural"

    tmpdir = tempfile.mkdtemp()
    segment_files = []

    async def run():
        for i, sent in enumerate(sentences):
            if not sent.strip():
                continue
            path = os.path.join(tmpdir, f"seg_{i}.mp3")
            await _generate_segment_async(voice, sent, path)
            segment_files.append((sent, path))

    asyncio.run(run())

    if not segment_files:
        return [(text.strip(), 0.0, 2.0)]

    # Audios zusammenfügen + Dauer pro Segment auslesen
    try:
        try:
            from moviepy import AudioFileClip, concatenate_audioclips
        except ImportError:
            from moviepy.editor import AudioFileClip, concatenate_audioclips
        clips = [AudioFileClip(p) for _, p in segment_files]
        durations = [c.duration for c in clips]
        final = concatenate_audioclips(clips)
        final.write_audiofile(output_audio_path, logger=None)
        final.close()
        for c in clips:
            c.close()
    except Exception:
        if len(segment_files) == 1:
            import shutil
            shutil.copy(segment_files[0][1], output_audio_path)
            try:
                from moviepy import AudioFileClip
            except ImportError:
                from moviepy.editor import AudioFileClip
            d = AudioFileClip(output_audio_path).duration
            return [(segment_files[0][0], 0.0, d)]
        raise

    # Aufräumen Temp
    for _, p in segment_files:
        try:
            os.remove(p)
        except OSError:
            pass
    try:
        os.rmdir(tmpdir)
    except OSError:
        pass

    # Timings: (satz, start, duration)
    timings = []
    t = 0.0
    for (sent, _), d in zip(segment_files, durations):
        timings.append((sent, t, d))
        t += d
    return timings
