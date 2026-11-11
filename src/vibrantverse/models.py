"""Thin wrappers around the AI4Bharat models and Wav2Lip, mirroring the calls used in the original Colab notebooks.
Heavy dependencies are imported lazily, so the document/subtitle utilities work without them.
Set-up of the model repositories/checkpoints is described in docs/SETUP.md (it follows the notebooks)."""
from __future__ import annotations

import subprocess
from pathlib import Path

LANGUAGES = {"hi": "Hindi", "bn": "Bengali", "mr": "Marathi", "gu": "Gujarati", "kn": "Kannada", "te": "Telugu",
             "ta": "Tamil", "ml": "Malayalam"}


def check_lang(lang: str) -> str:
    if lang not in LANGUAGES:
        raise ValueError(f"Unsupported language '{lang}'. Choose one of: {', '.join(LANGUAGES)}")
    return lang


class Translator:
    """IndicTrans (v1) English -> Indic, via `indicTrans.inference.engine.Model(expdir='en-indic')`."""

    def __init__(self, expdir: str = "en-indic"):
        from indicTrans.inference.engine import Model  # noqa: requires the indicTrans repo + fairseq on PYTHONPATH

        self.model = Model(expdir=expdir)

    def translate(self, text: str, lang: str) -> str:
        return self.model.translate_paragraph(text, "en", check_lang(lang))


class Transliterator:
    """IndicXlit Roman -> native script (`ai4bharat-transliteration`)."""

    def __init__(self, lang: str, beam_width: int = 10):
        from ai4bharat.transliteration import XlitEngine

        self.lang = check_lang(lang)
        self.engine = XlitEngine([self.lang], beam_width=beam_width, src_script_type="en")

    def __call__(self, text: str) -> str:
        out = self.engine.translit_sentence(text)
        if isinstance(out, dict):  # multi-language engines return {lang: text}
            out = out.get(self.lang, next(iter(out.values())))
        return out


class Speaker:
    """IndicTTS FastPitch + HiFi-GAN (Coqui TTS `Synthesizer`) with AI4Bharat's TextToSpeechEngine pre-processing."""

    def __init__(self, lang: str, checkpoints: str = "checkpoints", use_cuda: bool = False):
        from TTS.utils.synthesizer import Synthesizer
        from src.inference import TextToSpeechEngine  # from the Indic-TTS/inference folder

        self.lang = check_lang(lang)
        c = Path(checkpoints) / lang
        synth = Synthesizer(
            tts_checkpoint=str(c / "fastpitch/best_model.pth"), tts_config_path=str(c / "fastpitch/config.json"),
            tts_speakers_file=str(c / "fastpitch/speakers.pth"), tts_languages_file=None,
            vocoder_checkpoint=str(c / "hifigan/best_model.pth"), vocoder_config=str(c / "hifigan/config.json"),
            encoder_checkpoint="", encoder_config="", use_cuda=use_cuda)
        self.engine = TextToSpeechEngine({lang: synth})
        self.sample_rate = 22050

    def synthesize(self, text: str, gender: str, wav_path: str, mp3_path: str | None = None) -> str:
        import numpy as np
        from scipy.io import wavfile

        audio = np.asarray(self.engine.infer_from_text(input_text=text, lang=self.lang, speaker_name=gender))
        pcm = np.int16(np.clip(audio, -1.0, 1.0) * 32767)      # float -> 16-bit PCM, clipped to avoid wrap-around
        wavfile.write(wav_path, self.sample_rate, pcm)
        if mp3_path:
            from pydub import AudioSegment
            AudioSegment.from_wav(wav_path).export(mp3_path, format="mp3")
        return wav_path


def lipsync(face_video: str, audio_wav: str, out_mp4: str, wav2lip_dir: str = "Wav2Lip", hd: bool = False,
            pads=(0, 10, 0, 0), resize_factor: int = 1, nosmooth: bool = True) -> str:
    """Run Wav2Lip inference (subprocess), as in the original notebook."""
    ckpt = Path(wav2lip_dir) / "checkpoints" / ("wav2lip_gan.pth" if hd else "wav2lip.pth")
    cmd = ["python", "inference.py", "--checkpoint_path", str(ckpt.resolve()), "--face", str(Path(face_video).resolve()),
           "--audio", str(Path(audio_wav).resolve()), "--outfile", str(Path(out_mp4).resolve()),
           "--pads", *map(str, pads), "--resize_factor", str(resize_factor)] + (["--nosmooth"] if nosmooth else [])
    subprocess.run(cmd, cwd=wav2lip_dir, check=True)
    return out_mp4


def burn_subtitles(video: str, srt: str, out_mp4: str, font_size: int = 16, font: str = "Noto Sans") -> str:
    """Hard-code subtitles with FFmpeg's `subtitles` filter. An Indic-capable font (e.g. Noto Sans Kannada/Devanagari)
    must be installed for the script to render."""
    style = (f"Fontname={font},Fontsize={font_size},PrimaryColour=&HFFFFFF&,BackColour=&H80000000&,"
             f"OutlineColour=&H000000&,Outline=2")
    cmd = ["ffmpeg", "-y", "-i", video, "-vf", f"subtitles={srt}:force_style='{style}'", "-c:a", "copy", out_mp4]
    subprocess.run(cmd, check=True, capture_output=True)
    return out_mp4
