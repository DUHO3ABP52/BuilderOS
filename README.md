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

## Что уже есть (0.5.0-alpha)

- Docker: API, PostgreSQL, Redis, MinIO, Qdrant, Ollama, Frontend
- JWT-авторизация и первый пользователь
- Компании и строительные объекты с архивированием
- Document Engine: `BuilderDocument`, секции, переменные, DOCX/PDF/HTML
- **Импорт образцов**: DOCX / PDF / TXT / фото → шаблон (OCR)
- Реестр шаблонов, версии, обучение на правках
- Библиотека блоков договора
- База знаний + RAG-поиск (Qdrant + embeddings)
- AI Core: Coordinator, Document / Knowledge / Memory / Task agents
- Локальная LLM (Ollama) + опциональный OmniRoute (hybrid)
- Задачи и корпоративная память
- Журнал событий
- Чат помощника в UI

Примеры запросов к помощнику:

- `сделай договор`
- `найди ГОСТ`
- `что говорит про гарантийный срок`
- `добавь задачу подписать акт`
- `запомни: гарантия всегда 24 месяца`

Подробности: [docs/ROADMAP.md](docs/ROADMAP.md), [docs/PROJECT.md](docs/PROJECT.md), [docs/LLM.md](docs/LLM.md), [docs/RAG.md](docs/RAG.md), [docs/SAMPLES.md](docs/SAMPLES.md).
