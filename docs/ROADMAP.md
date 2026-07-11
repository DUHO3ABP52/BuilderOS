# Дорожная карта

## Sprint 0 — Foundation

- [x] Архитектура и структура репозитория
- [x] Docker Compose (API, PostgreSQL, Redis, MinIO, Qdrant, Frontend)
- [x] FastAPI + Alembic + health-check

## Alpha 0.1 — ядро данных

- [x] Контрагенты
- [x] Строительные объекты
- [x] Аутентификация и первый пользователь
- [x] Журнал событий и архивирование вместо удаления
- [x] Dashboard UI

## Alpha 0.2 — Document Engine

- [x] Формат BuilderDocument (секции + переменные)
- [x] Реестр шаблонов и версий
- [x] Библиотека блоков
- [x] Документ, версии и связь с объектом
- [x] Заполнение переменных
- [x] Экспорт DOCX / PDF / HTML
- [x] Импорт DOCX → BuilderDocument
- [x] Каркас базы знаний (без RAG)

## Alpha 0.3 — AI Core

- [x] Coordinator (диспетчер запросов)
- [x] Document Agent
- [x] Knowledge Agent
- [x] Memory Agent
- [x] Task Agent
- [x] UI чата помощника
- [x] Локальная LLM через Ollama (автозапуск + pull модели)
- [x] Опциональный OmniRoute (hybrid: локально → бесплатный gateway)

BuilderOS перешёл от хранения документов к цифровому сотруднику с агентами.

## Дальше

- RAG по СП/ГОСТ/СНиП (Qdrant + эмбеддинги);
- более крупные локальные модели (14B/32B) под мощное железо;
- обучение на правках пользователя;
- задачи, финансы, календарь и корпоративная память.
