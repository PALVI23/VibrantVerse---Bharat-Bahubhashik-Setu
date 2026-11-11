"""End-to-end pipeline and command-line interface.

    python -m vibrantverse.pipeline translate  --input examples/sample_input.docx --lang kn --out out/kn.docx
    python -m vibrantverse.pipeline speak      --input out/kn.docx --lang kn --gender female --out out/kn.mp3
    python -m vibrantverse.pipeline video      --face avatar.mp4 --audio out/kn.wav --text out/kn.docx --out out/kn.mp4
    python -m vibrantverse.pipeline all        --input examples/sample_input.docx --lang kn --face avatar.mp4 --out-dir out
"""
from __future__ import annotations

import argparse
from pathlib import Path

from . import document as D
from . import subtitles as S


def translate_document(input_docx, lang, out_docx, translator=None, transliterator=None) -> list[D.Segment]:
    """English curated DOCX -> target-language DOCX. Paragraphs/headings are translated with IndicTrans; {{terms}}
    are carried through translation and then transliterated with IndicXlit (as in the original notebook)."""
    from .models import Transliterator, Translator, check_lang

    check_lang(lang)                     # fail fast, before loading any model
    translator = translator or Translator()
    transliterator = transliterator or Transliterator(lang)
    segments = D.parse_segments(D.read_docx_text(input_docx))
    out = []
    for s in segments:
        translated = translator.translate(s.text, lang)
        out.append(D.Segment(s.kind, D.transliterate_marked(translated, transliterator)))
    D.write_docx(out, out_docx)
    return out


def speak_document(input_docx, lang, gender, out_audio, checkpoints="checkpoints") -> str:
    from .models import Speaker, check_lang

    check_lang(lang)
    text = D.strip_markers(D.read_docx_text(input_docx))
    out_audio = Path(out_audio)
    wav = str(out_audio.with_suffix(".wav"))
    Speaker(lang, checkpoints).synthesize(text, gender, wav, str(out_audio) if out_audio.suffix == ".mp3" else None)
    return wav


def make_video(face, audio_wav, text_docx, out_mp4, wav2lip_dir="Wav2Lip", hd=False) -> str:
    from pydub import AudioSegment

    from .models import burn_subtitles, lipsync

    out_mp4 = Path(out_mp4)
    raw = str(out_mp4.with_name(out_mp4.stem + "_nosubs.mp4"))
    lipsync(face, audio_wav, raw, wav2lip_dir, hd=hd)
    srt = out_mp4.with_suffix(".srt")
    srt.write_text(S.srt_from_text(D.strip_markers(D.read_docx_text(text_docx)), len(AudioSegment.from_file(audio_wav))),
                   encoding="utf-8")
    return burn_subtitles(raw, str(srt), str(out_mp4))


def main(argv=None):
    p = argparse.ArgumentParser(prog="vibrantverse", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("translate"); t.add_argument("--input", required=True); t.add_argument("--lang", required=True); t.add_argument("--out", required=True)
    s = sub.add_parser("speak"); s.add_argument("--input", required=True); s.add_argument("--lang", required=True)
    s.add_argument("--gender", choices=["male", "female"], default="female"); s.add_argument("--out", required=True)
    s.add_argument("--checkpoints", default="checkpoints")
    v = sub.add_parser("video"); v.add_argument("--face", required=True); v.add_argument("--audio", required=True)
    v.add_argument("--text", required=True); v.add_argument("--out", required=True); v.add_argument("--wav2lip-dir", default="Wav2Lip")
    v.add_argument("--hd", action="store_true")
    a = sub.add_parser("all"); a.add_argument("--input", required=True); a.add_argument("--lang", required=True)
    a.add_argument("--face", required=True); a.add_argument("--gender", default="female"); a.add_argument("--out-dir", default="out")
    args = p.parse_args(argv)

    if args.cmd == "translate":
        translate_document(args.input, args.lang, args.out)
    elif args.cmd == "speak":
        speak_document(args.input, args.lang, args.gender, args.out, args.checkpoints)
    elif args.cmd == "video":
        make_video(args.face, args.audio, args.text, args.out, args.wav2lip_dir, args.hd)
    else:
        out = Path(args.out_dir); out.mkdir(parents=True, exist_ok=True)
        docx = out / f"translated_{args.lang}.docx"
        translate_document(args.input, args.lang, docx)
        wav = speak_document(docx, args.lang, args.gender, out / f"audio_{args.lang}.mp3")
        make_video(args.face, wav, docx, out / f"video_{args.lang}.mp4")


if __name__ == "__main__":
    main()
