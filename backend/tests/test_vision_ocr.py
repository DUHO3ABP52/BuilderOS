from io import BytesIO
from unittest.mock import patch

from PIL import Image, ImageDraw, ImageFont

from app.modules.documents.engine.sample_import import extract_text_from_image, extract_text_from_pdf
from app.services.vision_ocr import _is_weak_ocr, extract_text_smart


def _blank_png() -> bytes:
    image = Image.new("RGB", (200, 80), color=(255, 255, 255))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _text_png(text: str = "ДОГОВОР") -> bytes:
    image = Image.new("RGB", (400, 120), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)
    draw.text((20, 40), text, fill=(0, 0, 0))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_weak_ocr_detection() -> None:
    assert _is_weak_ocr("") is True
    assert _is_weak_ocr("abc") is True
    assert _is_weak_ocr("ДОГОВОР ПОДРЯДА № 12/26 г. Москва Заказчик ООО Ромашка Подрядчик") is False


def test_extract_text_smart_uses_vision_when_tesseract_weak() -> None:
    payload = _blank_png()
    with (
        patch("app.services.vision_ocr.tesseract_ocr", return_value=("", [])),
        patch("app.services.vision_ocr.settings") as settings_mock,
        patch("app.services.vision_ocr.llm_service.llm_is_configured", return_value=True),
        patch(
            "app.services.vision_ocr.vision_ocr",
            return_value=("ДОГОВОР ПОДРЯДА № 12/26\nЗаказчик: ООО Ромашка", ["OCR: vision (llava:7b)"]),
        ),
    ):
        settings_mock.llm_vision_enabled = True
        settings_mock.llm_vision_min_chars = 40
        text, warnings = extract_text_smart(payload)
    assert "ДОГОВОР" in text
    assert any("vision" in item.lower() for item in warnings)


def test_extract_text_smart_keeps_tesseract_when_strong() -> None:
    payload = _text_png()
    strong = "ДОГОВОР ПОДРЯДА № 12/26 г. Москва. Заказчик ООО Тест. Подрядчик ИП Иванов. Стоимость 1500000."
    with (
        patch("app.services.vision_ocr.tesseract_ocr", return_value=(strong, [])),
        patch("app.services.vision_ocr.settings") as settings_mock,
        patch("app.services.vision_ocr.llm_service.llm_is_configured", return_value=True),
        patch("app.services.vision_ocr.vision_ocr") as vision_mock,
    ):
        settings_mock.llm_vision_enabled = True
        settings_mock.llm_vision_min_chars = 40
        text, warnings = extract_text_smart(payload)
        vision_mock.assert_not_called()
    assert text == strong
    assert any("tesseract" in item.lower() for item in warnings)


def test_extract_text_from_image_delegates() -> None:
    with patch(
        "app.modules.documents.engine.sample_import.extract_text_smart",
        return_value=("hello", ["OCR: tesseract"]),
    ) as mocked:
        text, warnings = extract_text_from_image(b"fake")
    mocked.assert_called_once()
    assert text == "hello"
    assert warnings == ["OCR: tesseract"]


def test_scan_pdf_runs_page_ocr() -> None:
    # minimal PDF without text layer is hard; mock rasterize + smart OCR
    with (
        patch("app.modules.documents.engine.sample_import.render_pdf_pages", return_value=[b"img"]),
        patch(
            "app.modules.documents.engine.sample_import.extract_text_smart",
            return_value=("ДОГОВОР ПОДРЯДА со скана", ["OCR: vision (llava:7b)"]),
        ),
        patch("pypdf.PdfReader") as reader_mock,
    ):
        page = type("P", (), {"extract_text": lambda self: ""})()
        reader_mock.return_value.pages = [page]
        text, warnings = extract_text_from_pdf(b"%PDF-fake")
    assert "ДОГОВОР" in text
    assert any("без текстового слоя" in item for item in warnings)
