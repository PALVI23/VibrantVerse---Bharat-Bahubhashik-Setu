import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from vibrantverse import document as D  # noqa: E402
from vibrantverse import subtitles as S  # noqa: E402
from vibrantverse.models import check_lang  # noqa: E402

SAMPLE = Path(__file__).resolve().parents[1] / "examples" / "sample_input.docx"


def test_parse_keeps_document_order():
    text = "# H1 #\n*p1 {{Atma}}*\n*p2*\n# H2 #\n*p3*"
    segs = D.parse_segments(text)
    assert [(s.kind, s.text) for s in segs] == [("heading", "H1"), ("paragraph", "p1 {{Atma}}"), ("paragraph", "p2"),
                                                ("heading", "H2"), ("paragraph", "p3")]


def test_terms_and_transliteration_markers():
    t = "seek the truth {{Satya}} via {{ Sadhana }}"
    assert D.terms(t) == ["Satya", "Sadhana"]
    assert D.transliterate_marked(t, str.upper) == "seek the truth SATYA via SADHANA"
    assert D.strip_markers(t) == "seek the truth Satya via Sadhana"


def test_sample_document_roundtrip(tmp_path):
    segs = D.parse_segments(D.read_docx_text(SAMPLE))
    assert [s.kind for s in segs] == ["heading", "paragraph", "paragraph"]
    assert len(D.terms(D.plain_text(segs))) == 8
    out = D.write_docx(segs, tmp_path / "out.docx")
    assert "Moksha" in D.read_docx_text(out)


def test_translate_document_with_stub_models(tmp_path):
    """End-to-end document flow with stand-in models (the real ones need GPUs/checkpoints)."""
    from vibrantverse.pipeline import translate_document

    class StubTranslator:  # keeps {{terms}} untouched, like IndicTrans does in practice
        def translate(self, text, lang):
            return f"[{lang}] " + text

    out = translate_document(SAMPLE, "kn", tmp_path / "kn.docx", translator=StubTranslator(),
                             transliterator=lambda w: f"<{w}>")
    assert out[0].text == "[kn] The Inner Journey"
    assert "<Satya>" in out[1].text and "{{" not in D.read_docx_text(tmp_path / "kn.docx")


def test_srt_timestamps_are_valid():
    assert S.srt_timestamp(0) == "00:00:00,000"
    assert S.srt_timestamp(3_723_456) == "01:02:03,456"


def test_srt_from_text_covers_duration_and_splits_indic_sentences():
    text = "ಮೊದಲ ವಾಕ್ಯ. ಎರಡನೆಯ ವಾಕ್ಯ। तीसरा वाक्य॥ " + "word " * 40
    srt = S.srt_from_text(text, 12_000, max_chars=60)
    blocks = [b for b in srt.strip().split("\n\n")]
    assert blocks[0].startswith("1\n00:00:00,000 --> ")
    assert blocks[-1].split("\n")[1].endswith("00:00:12,000")
    assert len(blocks) >= 5 and all(len(b.split("\n")[2]) <= 60 for b in blocks)


def test_language_validation():
    assert check_lang("kn") == "kn"
    with pytest.raises(ValueError):
        check_lang("fr")
