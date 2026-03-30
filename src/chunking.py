from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ChunkingSettings:
    chunk_size: int = 12000
    chunk_overlap: int = 400
    split_strategy: str = "smart"  # smart | separator | paragraphs | chars
    custom_separator: str = r"_{3,}|-{3,}|={3,}"


def _split_paragraphs(text: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n{2,}", text or "") if p.strip()]


def _split_by_separator(text: str, separator_pattern: str) -> list[str]:
    try:
        re_sep = re.compile(rf"^\s*(?:{separator_pattern})\s*$", re.MULTILINE)
    except re.error:
        re_sep = re.compile(r"^\s*[-_=]{3,}\s*$", re.MULTILINE)

    parts = [p.strip() for p in re_sep.split(text or "") if p.strip()]
    return parts or _split_paragraphs(text)


def _split_by_chars(text: str, size: int, overlap: int) -> list[str]:
    if not text:
        return []
    size = max(1, int(size))
    overlap = max(0, int(overlap))
    step = max(1, size - overlap)
    return [text[i : i + size] for i in range(0, len(text), step)]


def _split_smart(text: str) -> list[str]:
    """
    Пытаемся резать по структуре:
    - заголовки/разделители (----, ____ и т.п.)
    - спикеры (оператор/клиент/агент...) если текст размечен построчно
    """
    lines = (text or "").split("\n")

    speaker_re = re.compile(
        r"^(?:\s*\[?\d{1,2}[:.]\d{2}(?::\d{2})?\]?\s*)?(?:оператор|клиент|менеджер|агент|customer|client|operator|agent)\s*[:\-]",
        re.IGNORECASE,
    )
    header_re = re.compile(r"^\s*(?:диалог|транскрипт|сессия|разговор|обращение)\b", re.IGNORECASE)
    sep_re = re.compile(r"^\s*[-_=]{3,}\s*$")

    blocks: list[str] = []
    cur: list[str] = []

    def flush() -> None:
        s = "\n".join(cur).strip()
        if s:
            blocks.append(s)
        cur.clear()

    for line in lines:
        joined = "\n".join(cur).strip()
        if (header_re.search(line) or sep_re.search(line)) and len(joined) > 300:
            flush()
        if speaker_re.search(line) and len(joined) > 300:
            flush()
        cur.append(line)

    flush()

    if len(blocks) < 3:
        return _split_paragraphs(text)
    return blocks


def _build_chunks(segments: list[str], chunk_size: int, overlap: int) -> list[str]:
    chunks: list[str] = []
    buf = ""

    def push() -> None:
        nonlocal buf
        s = buf.strip()
        if s:
            chunks.append(s)
        buf = ""

    for seg in segments:
        cand = f"{buf}\n\n{seg}" if buf else seg
        if len(cand) <= chunk_size:
            buf = cand
            continue

        if not buf:
            chunks.extend(_split_by_chars(seg, chunk_size, overlap))
            continue

        push()
        buf = seg

    push()

    if overlap > 0 and len(chunks) > 1:
        out = [chunks[0]]
        for i in range(1, len(chunks)):
            tail = chunks[i - 1][-overlap:]
            merged = f"{tail}\n\n{chunks[i]}"
            out.append(merged if len(merged) <= chunk_size * 1.15 else chunks[i])
        return out

    return chunks


def make_chunks(text: str, settings: ChunkingSettings) -> list[str]:
    chunk_size = int(settings.chunk_size)
    chunk_overlap = int(settings.chunk_overlap)
    chunk_overlap = max(0, min(chunk_overlap, int(chunk_size * 0.4)))

    combined = (text or "").strip()
    if not combined:
        return []

    strategy = settings.split_strategy
    if strategy == "smart":
        segments = _split_smart(combined)
    elif strategy == "separator":
        segments = _split_by_separator(combined, settings.custom_separator)
    elif strategy == "paragraphs":
        segments = _split_paragraphs(combined)
    elif strategy == "chars":
        return _split_by_chars(combined, chunk_size, chunk_overlap)
    else:
        segments = _split_smart(combined)

    return _build_chunks(segments, chunk_size, chunk_overlap)

