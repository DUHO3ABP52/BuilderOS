# Дорожная карта

## Sprint 0 — Foundation

- [x] Архитектура и структура репозитория
- [x] Docker Compose (API, PostgreSQL, Redis, MinIO, Qdrant, Frontend)
- [x] FastAPI + Alembic + health-check

## Alpha 0.1 — ядро данных

- [x] Контрагенты / объекты / auth / audit / UI

## Alpha 0.2 — Document Engine

- [x] BuilderDocument, шаблоны, блоки, экспорт DOCX/PDF/HTML

## Alpha 0.3 — AI Core

- [x] Coordinator + агенты + Ollama/OmniRoute

## Alpha 0.4 — RAG

- [x] Qdrant + embeddings + семантический поиск знаний

## Alpha 0.5 — Образцы и обучение

- [x] Загрузка образца в любом формате (DOCX / PDF / TXT / фото)
- [x] OCR для изображений (Tesseract rus+eng)
- [x] Разбор образца → секции → переменные → шаблон
- [x] Предпросмотр импорта
- [x] Обучение Memory на правках версий шаблона
- [x] Подсказки Document Agent из памяти правок

## Alpha 0.6 — Финансы и календарь

- [x] Платежи (приход/расход, статусы, сводка)
- [x] Календарь событий (встречи, выезды, сроки)
- [x] Finance / Calendar agents + intents в координаторе
- [x] UI разделы и виджеты на dashboard

## Alpha 0.7 — Vision OCR

- [x] Умный OCR: Tesseract + vision-LLM (Ollama)
- [x] OCR скан-PDF (растр страниц)
- [x] Сканы не уходят в облако по умолчанию
- [x] Статус vision в `/ai/llm-status` и UI

## Alpha 0.8 — Knowledge graph объекта

- [x] Автограф связей вокруг Project
- [x] Ручные рёбра `graph_edges`
- [x] Graph Agent + intent `project_context`
- [x] Память с фильтром по `project_id`
- [x] UI «Граф объекта»

## Alpha 0.9 — Teacher-контур

- [x] Обезличивание ПДн/реквизитов перед облаком
- [x] Вопрос учителю через OmniRoute (`chat_teacher`)
- [x] Сохранение PATTERN (`source=teacher`) по confirm
- [x] API preview/ask + статус в `/ai/llm-status`
- [x] Документация [LEARNING.md](LEARNING.md)

## Дальше

- визуализация графа / автоизвлечение связей из документов;
- подсказки Document Agent из teacher-паттернов.
