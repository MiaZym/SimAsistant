from __future__ import annotations

import io
import os

import pandas as pd
from docx import Document
from pypdf import PdfReader


def extract_text(filename: str, file_bytes: bytes) -> str:
    """
    Минимальный набор извлечения текста:
    - pdf: pypdf
    - docx: python-docx
    - xlsx/xls: pandas + openpyxl (для xls может не поддерживаться)
    - txt: decode utf-8/latin1
    """
    ext = os.path.splitext(filename)[1].lower().lstrip(".")

    if ext == "pdf":
        return _extract_pdf(file_bytes)
    if ext == "docx":
        return _extract_docx(file_bytes)
    if ext in {"xlsx", "xls"}:
        return _extract_excel(file_bytes, filename)
    if ext == "txt":
        return _decode_text(file_bytes)
    if ext == "doc":
        raise ValueError('Формат ".doc" не поддерживается напрямую. Используйте .docx.')
    raise ValueError(f"Неподдерживаемый формат файла: .{ext}")


def _decode_text(b: bytes) -> str:
    for enc in ("utf-8", "utf-8-sig", "cp1251", "latin1"):
        try:
            return b.decode(enc)
        except Exception:
            continue
    return b.decode("latin1", errors="replace")


def _extract_pdf(file_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(file_bytes))
    parts: list[str] = []
    for page in reader.pages:
        txt = page.extract_text() or ""
        if txt.strip():
            parts.append(txt)
    return "\n".join(parts).strip()


def _extract_docx(file_bytes: bytes) -> str:
    doc = Document(io.BytesIO(file_bytes))
    parts: list[str] = []
    for para in doc.paragraphs:
        if para.text and para.text.strip():
            parts.append(para.text)
    return "\n".join(parts).strip()


def _extract_excel(file_bytes: bytes, _filename: str) -> str:
    # pandas обычно работает с xlsx via openpyxl; для xls может понадобиться другой engine
    bio = io.BytesIO(file_bytes)
    with pd.ExcelFile(bio) as xls:
        parts: list[str] = []
        for sheet in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name=sheet, header=None)
            csv = df.to_csv(index=False)
            parts.append(f"=== Лист: {sheet} ===\n{csv}")
        return "\n".join(parts).strip()

