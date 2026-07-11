# Импорт образцов → шаблоны

## Зачем

Пользователь загружает готовый договор/акт (Word, PDF, фото) как образец.
BuilderOS извлекает текст, делит на секции, находит переменные и создаёт шаблон.

## Поддерживаемые форматы

| Формат | Как разбирается |
|---|---|
| DOCX | python-docx |
| PDF (с текстовым слоем) | pypdf |
| PDF (скан без текста) | растр страниц → OCR |
| TXT / MD | напрямую |
| PNG / JPG / WEBP / TIFF | OCR |

## OCR

1. **Tesseract** (`rus+eng`) — быстрый локальный слой.
2. Если текст слабый/пустой и включён Vision — **vision-LLM** (по умолчанию `llava:7b` в Ollama).
3. Сканы договоров **не уходят в облако** (`LLM_CLOUD_FOR_VISION=false`).

В preview/импорте warnings показывают движок: `OCR: tesseract` или `OCR: vision (…)`.

Для русского текста на сложных сканах можно поставить `LLM_VISION_MODEL=qwen2.5vl:7b`.

## API

- `POST /api/v1/templates/import/preview` — разобрать без сохранения
- `POST /api/v1/templates/import/sample` — создать шаблон из файла
- `POST /api/v1/templates/import/docx` — старый путь (совместимость)

Multipart поля: `file`, опционально `name`, `slug`, `category`.

## Обучение на правках

При создании новой версии шаблона система сравнивает секции с предыдущей
и сохраняет PATTERN / TEMPLATE_HINT в Memory. Document Agent показывает эти
подсказки при подготовке следующего документа.
