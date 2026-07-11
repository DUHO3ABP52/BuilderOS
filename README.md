# BuilderOS

Локальная операционная система строительного ИП: объекты, контрагенты,
документы, шаблоны, задачи и ИИ-помощник.

## Быстрый запуск

1. Скопируйте `.env.example` в `.env` и задайте безопасные пароли.
2. Выполните `docker compose up --build` — поднимутся приложение, Ollama и индекс знаний.
3. Откройте UI: `http://localhost:3000`
4. API / Swagger: `http://localhost:8000/docs`

Опционально бесплатный cloud-gateway: `docker compose --profile omniroute up --build`  
(см. [docs/LLM.md](docs/LLM.md), [OmniRoute](https://github.com/diegosouzapw/OmniRoute)).

Учётная запись по умолчанию (из `.env`):

- email: `admin@example.com`
- password: `change-me`

## Что уже есть (0.9.0-alpha)

- Docker: API, PostgreSQL, Redis, MinIO, Qdrant, Ollama, Frontend
- JWT-авторизация и первый пользователь
- Компании и строительные объекты с архивированием
- Document Engine: `BuilderDocument`, секции, переменные, DOCX/PDF/HTML
- **Импорт образцов**: DOCX / PDF / TXT / фото → шаблон
- **Vision OCR**: Tesseract + локальная vision-LLM
- **Knowledge graph** объекта
- **Teacher-контур**: обезличенный вопрос → OmniRoute → локальный PATTERN
- Реестр шаблонов, версии, обучение на правках
- База знаний + RAG
- AI Core: Coordinator + агенты (включая Graph / Teacher)
- Финансы и календарь
- Задачи, память, журнал, UI-чат

Примеры:

- `спроси учителя: как обычно формулируют гарантию`
- `контекст объекта`
- `сделай договор`
- `найди ГОСТ`
- `добавь платёж аванс 150000`

Подробности: [docs/LEARNING.md](docs/LEARNING.md), [docs/GRAPH.md](docs/GRAPH.md), [docs/ROADMAP.md](docs/ROADMAP.md), [docs/LLM.md](docs/LLM.md).
