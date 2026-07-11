from __future__ import annotations

import logging
import mimetypes
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from app.modules.documents.engine.builder_document import BuilderDocument, VariableDefinition
from app.modules.documents.engine.parser import parse_docx
from app.modules.documents.engine.text_parser import detect_doc_type, parse_plain_text, templatize_document
from app.services.vision_ocr import extract_text_smart, render_pdf_pages

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SampleImportResult:
    document: BuilderDocument
    variables: list[VariableDefinition]
    sample_values: dict
    source_format: str
    extracted_text: str
    warnings: list[str]


def _guess_format(filename: str | None, content_type: str | None, data: bytes) -> str:
    name = (filename or "").lower()
    ctype = (content_type or "").lower()
    if name.endswith(".docx") or "wordprocessingml" in ctype:
        return "docx"
    if name.endswith(".pdf") or ctype == "application/pdf":
        return "pdf"
    if name.endswith((".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".bmp")) or ctype.startswith("image/"):
        return "image"
    if name.endswith((".txt", ".md")) or ctype.startswith("text/"):
        return "text"
    # magic bytes
    if data[:4] == b"%PDF":
        return "pdf"
    if data[:2] == b"PK":
        return "docx"
    if data[:8] == b"\x89PNG\r\n\x1a\n" or data[:2] == b"\xff\xd8":
        return "image"
    return "text"


def extract_text_from_pdf(data: bytes) -> tuple[str, list[str]]:
    warnings: list[str] = []
    try:
        from pypdf import PdfReader
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("Библиотека pypdf не установлена") from exc

    reader = PdfReader(BytesIO(data))
    pages: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        if text.strip():
            pages.append(text)
    joined = "\n".join(pages).strip()
    if joined:
        return joined, warnings

    warnings.append("PDF без текстового слоя — OCR страниц (Tesseract / vision).")
    try:
        images = render_pdf_pages(data, max_pages=5)
    except Exception as exc:
        logger.info("PDF rasterize failed: %s", exc)
        warnings.append("Не удалось растрировать PDF. Загрузите фото страниц.")
        return "", warnings

    ocr_parts: list[str] = []
    for index, image_bytes in enumerate(images, start=1):
        page_text, page_warnings = extract_text_smart(image_bytes)
        warnings.extend([f"стр.{index}: {item}" for item in page_warnings])
        if page_text.strip():
            ocr_parts.append(page_text.strip())
    joined = "\n\n".join(ocr_parts).strip()
    if not joined:
        warnings.append("OCR не извлёк текст из скан-PDF.")
    return joined, warnings


def extract_text_from_image(data: bytes) -> tuple[str, list[str]]:
    return extract_text_smart(data)


def extract_text_from_bytes(
    data: bytes,
    *,
    filename: str | None = None,
    content_type: str | None = None,
) -> tuple[str, str, list[str]]:
    source_format = _guess_format(filename, content_type, data)
    warnings: list[str] = []

    if source_format == "docx":
        document = parse_docx(data)
        text = "\n".join(f"{section.title}\n{section.content}" for section in document.sections)
        return text, source_format, warnings
    if source_format == "pdf":
        text, warnings = extract_text_from_pdf(data)
        return text, source_format, warnings
    if source_format == "image":
        text, warnings = extract_text_from_image(data)
        return text, source_format, warnings

    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        text = data.decode("cp1251", errors="ignore")
        warnings.append("Текст декодирован как cp1251.")
    return text, "text", warnings


def import_sample_to_builder_document(
    data: bytes,
    *,
    filename: str | None = None,
    content_type: str | None = None,
    title: str | None = None,
) -> SampleImportResult:
    text, source_format, warnings = extract_text_from_bytes(data, filename=filename, content_type=content_type)
    if not text.strip():
        raise ValueError("Не удалось извлечь текст из файла. Проверьте качество фото/скана.")

    stem = Path(filename or "sample").stem
    resolved_title = title or stem.replace("_", " ").replace("-", " ").strip() or "Импортированный образец"
    doc_type = detect_doc_type(text)

    if source_format == "docx":
        base = parse_docx(data).model_copy(update={"title": resolved_title, "doc_type": doc_type})
    else:
        base = parse_plain_text(text, title=resolved_title, doc_type=doc_type)

    templated, variables, sample_values = templatize_document(base)
    templated.metadata = {
        **(templated.metadata or {}),
        "source_format": source_format,
        "source_filename": filename,
        "content_type": content_type or mimetypes.guess_type(filename or "")[0],
        "warnings": warnings,
    }
    return SampleImportResult(
        document=templated,
        variables=variables,
        sample_values=sample_values,
        source_format=source_format,
        extracted_text=text,
        warnings=warnings,
    )
