from __future__ import annotations

import html
import re
from pathlib import Path
from typing import Iterable, List, Optional


def clean_caption_text(text: str) -> str:
    text = html.unescape(text)
    text = re.sub(r"<\d{2}:\d{2}:\d{2}\.\d{3}>", " ", text)
    text = re.sub(r"</?c[^>]*>", " ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"\[(?:music|applause|laughter|noise|sound|silence)\]", " ", text, flags=re.I)
    text = re.sub(r"\((?:music|applause|laughter|noise|sound|silence)\)", " ", text, flags=re.I)
    text = re.sub(r"♪+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def parse_subtitle_file(path: Path) -> List[str]:
    raw = path.read_text(encoding="utf-8", errors="ignore")
    captions: List[str] = []
    current: List[str] = []
    skip_note_block = False

    for original_line in raw.splitlines():
        line = original_line.strip()
        if not line:
            if current:
                captions.append(clean_caption_text(" ".join(current)))
                current = []
            skip_note_block = False
            continue
        if line.upper().startswith("NOTE"):
            skip_note_block = True
            continue
        if skip_note_block:
            continue
        if line.upper().startswith(("WEBVTT", "STYLE", "REGION")):
            continue
        if line.startswith(("Kind:", "Language:")):
            continue
        if "-->" in line:
            continue
        if re.fullmatch(r"\d+", line):
            continue
        if re.match(r"^X-TIMESTAMP-MAP=", line):
            continue

        cleaned = clean_caption_text(line)
        if cleaned:
            current.append(cleaned)

    if current:
        captions.append(clean_caption_text(" ".join(current)))
    return [caption for caption in captions if caption]


def norm_word(word: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", word.lower())


def append_with_overlap(output_words: List[str], new_words: List[str]) -> None:
    if not new_words:
        return
    if not output_words:
        output_words.extend(new_words)
        return

    best = 0
    max_k = min(len(output_words), len(new_words), 100)
    for k in range(max_k, 0, -1):
        if [norm_word(w) for w in output_words[-k:]] == [norm_word(w) for w in new_words[:k]]:
            best = k
            break
    output_words.extend(new_words[best:])


def make_readable_paragraphs(text: str) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    paragraphs: List[str] = []
    current: List[str] = []
    length = 0

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        current.append(sentence)
        length += len(sentence)
        if length >= 450 or len(current) >= 5:
            paragraphs.append(" ".join(current))
            current = []
            length = 0

    if current:
        paragraphs.append(" ".join(current))
    return "\n\n".join(paragraphs).strip() + "\n"


def dedupe_captions(captions: Iterable[str]) -> str:
    output_words: List[str] = []
    previous_norm = ""

    for caption in captions:
        caption = clean_caption_text(caption)
        if not caption:
            continue
        current_norm = re.sub(r"\W+", "", caption.lower())
        if current_norm == previous_norm:
            continue
        previous_norm = current_norm
        append_with_overlap(output_words, caption.split())

    text = clean_caption_text(" ".join(output_words))
    text = re.sub(r"\s+([,.!?;:])", r"\1", text)
    text = re.sub(r"([.!?])\s+", r"\1 ", text)
    text = re.sub(r"\bi\b", "I", text)
    return make_readable_paragraphs(text)


def clean_subtitle_file_to_txt(subtitle_path: Path, output_txt_path: Optional[Path] = None) -> Path:
    if output_txt_path is None:
        output_txt_path = subtitle_path.with_suffix(".clean.txt")
    clean_text = dedupe_captions(parse_subtitle_file(subtitle_path))
    output_txt_path.write_text(clean_text, encoding="utf-8")
    return output_txt_path


def find_subtitle_files(folder: Path) -> List[Path]:
    files = [path for path in folder.rglob("*") if path.is_file() and path.suffix.lower() in {".vtt", ".srt"}]
    return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)
