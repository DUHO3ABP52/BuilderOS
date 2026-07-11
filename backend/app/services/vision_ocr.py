from __future__ import annotations

import base64
import logging
import re
from io import BytesIO

from app.core.config import settings
from app.services import llm as llm_service
from app.services.llm import LLMError

logger = logging.getLogger(__name__)

_VISION_OCR_PROMPT = (
    "Ты OCR для строительных документов РФ (договоры, акты, сметы, КС-2/КС-3).\n"
    "Извлеки весь видимый текст с изображения точно, без выдумок и без комментариев.\n"
    "Сохраняй структуру: заголовки, нумерацию пунктов, переносы строк, ИНН и суммы как есть.\n"
    "Если текст неразборчив — пропусти фрагмент, не угадывай.\n"
    "Верни только текст документа."
)


def _prepare_jpeg_b64(data: bytes, *, max_side: int = 1600) -> str:
    from PIL import Image

    image = Image.open(BytesIO(data))
    if image.mode not in {"RGB", "L"}:
        image = image.convert("RGB")
    else:
        image = image.convert("RGB")
    width, height = image.size
    longest = max(width, height)
    if longest > max_side:
        scale = max_side / float(longest)
        image = image.resize((max(1, int(width * scale)), max(1, int(height * scale))))
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=85, optimize=True)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def _russian_signal(text: str) -> int:
    return len(re.findall(r"[А-Яа-яЁё]", text or ""))


def _is_weak_ocr(text: str) -> bool:
    cleaned = (text or "").strip()
    if len(cleaned) < settings.llm_vision_min_chars:
        return True
    # мало кириллицы на типичном договоре — вероятно плохой OCR
    if _russian_signal(cleaned) < max(8, settings.llm_vision_min_chars // 4):
        return True
    return False


def tesseract_ocr(data: bytes) -> tuple[str, list[str]]:
    warnings: list[str] = []
    try:
        from PIL import Image
        import pytesseract
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("Для OCR нужны Pillow и pytesseract") from exc

    image = Image.open(BytesIO(data))
    if image.mode not in {"RGB", "L"}:
        image = image.convert("RGB")
    try:
        text = pytesseract.image_to_string(image, lang="rus+eng")
    except Exception:
        warnings.append("Русский OCR pack недоступен, использован eng.")
        text = pytesseract.image_to_string(image, lang="eng")
    cleaned = (text or "").strip()
    if not cleaned:
        warnings.append("Tesseract не распознал текст на изображении.")
    return cleaned, warnings


def vision_ocr(data: bytes) -> tuple[str, list[str]]:
    warnings: list[str] = []
    if not settings.llm_vision_enabled:
        raise LLMError("Vision OCR отключён")
    if not llm_service.llm_is_configured():
        raise LLMError("LLM отключена")

    image_b64 = _prepare_jpeg_b64(data)
    content = [
        {"type": "text", "text": _VISION_OCR_PROMPT},
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
    ]
    text = llm_service.chat_vision(
        [{"role": "user", "content": content}],
        temperature=0.0,
        max_tokens=settings.llm_vision_max_tokens,
        allow_cloud=settings.llm_cloud_for_vision,
    )
    cleaned = (text or "").strip()
    # модели иногда оборачивают ответ
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:text|markdown)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned).strip()
    if not cleaned:
        warnings.append("Vision OCR вернул пустой текст.")
    else:
        warnings.append(f"OCR: vision ({settings.llm_vision_model})")
    return cleaned, warnings


def extract_text_smart(data: bytes) -> tuple[str, list[str]]:
    """Tesseract → при слабом результате Vision-LLM → лучший текст."""
    warnings: list[str] = []
    tess_text, tess_warnings = tesseract_ocr(data)
    warnings.extend(tess_warnings)

    use_vision = settings.llm_vision_enabled and llm_service.llm_is_configured()
    if use_vision and _is_weak_ocr(tess_text):
        try:
            vision_text, vision_warnings = vision_ocr(data)
            warnings.extend(vision_warnings)
            if vision_text and (not tess_text or len(vision_text) > len(tess_text) * 0.8):
                return vision_text, warnings
            if tess_text and vision_text and len(vision_text) <= len(tess_text) * 0.8:
                warnings.append("Vision OCR слабее Tesseract — оставлен Tesseract.")
        except Exception as exc:
            logger.info("Vision OCR fallback to Tesseract: %s", exc)
            warnings.append(f"Vision OCR недоступен ({exc}), использован Tesseract.")
    elif tess_text:
        warnings.append("OCR: tesseract")

    return tess_text, warnings


def render_pdf_pages(data: bytes, *, max_pages: int = 5, scale: float = 2.0) -> list[bytes]:
    """Растрирует страницы PDF для OCR сканов."""
    import pypdfium2 as pdfium

    pdf = pdfium.PdfDocument(data)
    images: list[bytes] = []
    limit = min(len(pdf), max_pages)
    for index in range(limit):
        page = pdf[index]
        bitmap = page.render(scale=scale)
        pil = bitmap.to_pil()
        buffer = BytesIO()
        pil.convert("RGB").save(buffer, format="JPEG", quality=85)
        images.append(buffer.getvalue())
    return images
