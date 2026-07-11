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

## Дальше

- более точный OCR/vision LLM для сложных сканов;
- финансы и календарь;
- корпоративная память и knowledge graph связей объекта.
