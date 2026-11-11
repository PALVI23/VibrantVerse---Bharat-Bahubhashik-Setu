"""Subtitle (SRT) generation.

The original notebook produced timestamps such as `0:00:05,000` (str(timedelta) + ",000"), which is not valid SRT
(`00:00:05,000` is required), and recognised speech with a hard-coded Hindi model regardless of the target language.
Since the pipeline already *knows* the translated text, `srt_from_text` builds subtitles directly from it, timing
each sentence in proportion to its length over the audio duration - no speech recognition needed.
"""
from __future__ import annotations

import re

ASR_LANGUAGE = {"hi": "hi-IN", "bn": "bn-IN", "mr": "mr-IN", "gu": "gu-IN", "kn": "kn-IN", "te": "te-IN",
                "ta": "ta-IN", "ml": "ml-IN"}

# sentence ends: Latin punctuation, Devanagari danda (। ॥) and newlines
_SENT_RE = re.compile(r"(?<=[.!?।॥])\s+|\n+")


def srt_timestamp(ms: float) -> str:
    ms = max(0, int(round(ms)))
    h, rem = divmod(ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def split_sentences(text: str, max_chars: int = 90) -> list[str]:
    """Sentence split, then wrap long sentences at word boundaries so each cue fits on screen."""
    cues = []
    for sent in (s.strip() for s in _SENT_RE.split(text)):
        if not sent:
            continue
        words, line = sent.split(), ""
        for w in words:
            if line and len(line) + 1 + len(w) > max_chars:
                cues.append(line)
                line = w
            else:
                line = f"{line} {w}".strip()
        if line:
            cues.append(line)
    return cues


def srt_from_cues(cues: list[tuple[float, float, str]]) -> str:
    return "".join(f"{i}\n{srt_timestamp(a)} --> {srt_timestamp(b)}\n{t}\n\n" for i, (a, b, t) in enumerate(cues, 1))


def srt_from_text(text: str, duration_ms: float, max_chars: int = 90) -> str:
    """Distribute the audio duration over subtitle cues in proportion to their character count."""
    cues = split_sentences(text, max_chars)
    if not cues:
        return ""
    total = sum(len(c) for c in cues)
    t, out = 0.0, []
    for c in cues:
        d = duration_ms * len(c) / total
        out.append((t, t + d, c))
        t += d
    return srt_from_cues(out)


def srt_from_audio(audio_path: str, lang: str, chunk_ms: int = 5000) -> str:
    """Original approach (speech recognition on fixed 5 s chunks), now with the correct language code."""
    import os
    import tempfile

    import speech_recognition as sr
    from pydub import AudioSegment

    audio = AudioSegment.from_file(audio_path)
    rec, cues = sr.Recognizer(), []
    for start in range(0, len(audio), chunk_ms):
        end = min(start + chunk_ms, len(audio))
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            audio[start:end].export(f.name, format="wav")
            with sr.AudioFile(f.name) as src:
                data = rec.record(src)
        os.unlink(f.name)
        try:
            text = rec.recognize_google(data, language=ASR_LANGUAGE.get(lang, "en-IN"))
        except (sr.UnknownValueError, sr.RequestError):
            text = ""
        if text:
            cues.append((start, end, text))
    return srt_from_cues(cues)
