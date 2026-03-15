"""TTS mit Satz-Timing für synchronen Lauftext. Unterstützt Edge TTS (kostenlos) und OpenAI TTS (natürlicher)."""
import asyncio
import os
import tempfile
from pathlib import Path
from typing import List, Tuple

# Edge TTS – deutsche Neural-Stimmen (kostenlos)
EDGE_VOICES_DE = [
    "de-DE-KatjaNeural",   # weiblich, klar
    "de-DE-ConradNeural",   # männlich, ruhig
    "de-DE-AmalaNeural",    # weiblich
    "de-DE-KillianNeural",  # männlich
]

# OpenAI TTS – sehr natürliche Stimmen (kostenpflichtig, z. B. nova, alloy, echo, fable, onyx, shimmer)
OPENAI_VOICES = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]


def clean_text_for_tts(text: str) -> str:
    """Bereinigt Text für natürliche Aussprache: Abkürzungen ausschreiben, Zahlen/Ordinale entfernen."""
    import re
    if not text or not text.strip():
        return text
    # Abkürzungen ausschreiben (damit TTS natürlich klingt)
    replacements = [
        (r"\bz\.\s*B\.\b", "zum Beispiel"),
        (r"\bz\. B\.\b", "zum Beispiel"),
        (r"\bbzw\.\b", "beziehungsweise"),
        (r"\betc\.\b", "und so weiter"),
        (r"\bevtl\.\b", "eventuell"),
        (r"\bu\.\s*a\.\b", "unter anderem"),
        (r"\bu\.a\.\b", "unter anderem"),
        (r"\bca\.\b", "circa"),
        (r"\bggf\.\b", "gegebenenfalls"),
        (r"\bbzw\b", "beziehungsweise"),
    ]
    for pattern, repl in replacements:
        text = re.sub(pattern, repl, text, flags=re.IGNORECASE)
    # 1. 2. 3. oder 1) 2) 3) entfernen
    text = re.sub(r"\d+[.)]\s+", "", text)
    text = re.sub(r"^\d+\s+", "", text)
    text = re.sub(r"(?<=[.!?])\s*\d+\s+", " ", text)
    # Erstens, Zweitens, ... entfernen
    text = re.sub(
        r"(?i)\b(Erstens|Zweitens|Drittens|Viertens|Fünftens|Sechstens|Siebtens|Achtens|Neuntens|Zehntens)\s*[,.]?\s*",
        "",
        text,
    )
    text = re.sub(r"  +", " ", text)
    text = re.sub(r"\s+([.,!?])", r"\1", text)
    return text.strip()


def _split_sentences(text: str) -> List[str]:
    """Teilt Text in Sätze (für synchrone Anzeige)."""
    import re
    text = text.strip()
    if not text:
        return []
    # Bei . ! ? oder Zeilenumbruch trennen, Abkürzungen grob erhalten
    parts = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [p.strip() for p in parts if p.strip()]


def _generate_segment_openai(voice: str, text: str, path: str, api_key: str) -> None:
    """Erzeugt Audio für einen Satz mit OpenAI TTS (natürlicher Klang)."""
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    response = client.audio.speech.create(
        model="tts-1-hd",
        voice=voice if voice in OPENAI_VOICES else "nova",
        input=text,
    )
    with open(path, "wb") as f:
        f.write(response.content)


async def _generate_segment_async(voice: str, text: str, path: str) -> None:
    """Erzeugt Audio für einen Satz mit Edge TTS."""
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
    Erzeugt Audio mit TTS und liefert Satz-Timings: [(satz, start_sec, duration_sec), ...].
    TTS_ENGINE=openai + OPENAI_API_KEY → OpenAI TTS (sehr natürlich).
    Sonst Edge TTS (kostenlos).
    """
    text = clean_text_for_tts(text)
    tts_engine = (os.getenv("TTS_ENGINE") or "").strip().lower()
    openai_key = (os.getenv("OPENAI_API_KEY") or "").strip()
    use_openai = tts_engine == "openai" and bool(openai_key)

    sentences = _split_sentences(text)
    if not sentences:
        sentences = [text[:500] or " "]

    if use_openai:
        voice = (voice or "nova").lower() if voice else "nova"
        if voice not in OPENAI_VOICES:
            voice = "nova"
    else:
        if not voice or voice == "auto":
            voice = "de-DE-KatjaNeural"
        try:
            import edge_tts
        except ImportError:
            from gtts import gTTS
            tts = gTTS(text=text, lang=lang, slow=False)
            tts.save(output_audio_path)
            try:
                from moviepy.editor import AudioFileClip
                dur = AudioFileClip(output_audio_path).duration
            except Exception:
                dur = max(3.0, len(text) / 12.0)
            return [(text.strip(), 0.0, dur)]

    tmpdir = tempfile.mkdtemp()
    segment_files = []

    if use_openai:
        for i, sent in enumerate(sentences):
            if not sent.strip():
                continue
            path = os.path.join(tmpdir, f"seg_{i}.mp3")
            try:
                _generate_segment_openai(voice, sent, path, openai_key)
                segment_files.append((sent, path))
            except Exception as e:
                try:
                    os.remove(path)
                except OSError:
                    pass
                raise RuntimeError(f"OpenAI TTS fehlgeschlagen: {e}") from e
    else:
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
