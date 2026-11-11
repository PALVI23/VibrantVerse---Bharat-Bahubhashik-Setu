"""Curated-document format and DOCX I/O.

VibrantVerse input documents use three light-weight markers:

    # Heading #            -> translated
    *Paragraph text ...*   -> translated
    {{Sanskrit term}}      -> NOT translated; transliterated into the target script (e.g. {{Atma}} -> ಆತ್ಮ)

The original notebooks extracted headings and paragraphs with two separate regexes and zipped them back together,
which loses the original order when a document has several paragraphs per heading. `parse_segments` keeps the order.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

HEADING_RE = re.compile(r"#\s*(.+?)\s*#")
PARAGRAPH_RE = re.compile(r"\*(.+?)\*", re.S)
TERM_RE = re.compile(r"\{\{\s*([^{}]+?)\s*\}\}")
_SEGMENT_RE = re.compile(r"#\s*(?P<h>.+?)\s*#|\*(?P<p>.+?)\*", re.S)


@dataclass
class Segment:
    kind: str  # "heading" | "paragraph"
    text: str


def read_docx_text(path: str | Path) -> str:
    from docx import Document

    return "\n".join(p.text for p in Document(str(path)).paragraphs)


def parse_segments(text: str) -> list[Segment]:
    """Headings and paragraphs in document order. Text outside markers is ignored (as in the original pipeline)."""
    out = []
    for m in _SEGMENT_RE.finditer(text):
        if m.group("h") is not None:
            out.append(Segment("heading", m.group("h").strip()))
        elif m.group("p") and m.group("p").strip():
            out.append(Segment("paragraph", " ".join(m.group("p").split())))
    return out


def terms(text: str) -> list[str]:
    """Delimited terms that must be transliterated, not translated."""
    return TERM_RE.findall(text)


def transliterate_marked(text: str, transliterate: Callable[[str], str]) -> str:
    """Replace every {{term}} (which survives translation unchanged) by its transliteration."""
    return TERM_RE.sub(lambda m: transliterate(m.group(1)), text)


def strip_markers(text: str) -> str:
    """{{term}} -> term (e.g. before text-to-speech if transliteration was skipped)."""
    return TERM_RE.sub(lambda m: m.group(1), text)


def write_docx(segments: list[Segment], path: str | Path) -> Path:
    from docx import Document

    doc = Document()
    for s in segments:
        if s.kind == "heading":
            doc.add_heading(s.text, level=2)
        else:
            doc.add_paragraph(s.text)
    doc.save(str(path))
    return Path(path)


def plain_text(segments: list[Segment]) -> str:
    return "\n\n".join(s.text for s in segments)
