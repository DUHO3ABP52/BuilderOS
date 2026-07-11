# BuilderOS

Локальная операционная система строительного ИП: объекты, контрагенты,
документы, шаблоны, задачи и ИИ-помощник.

## Быстрый запуск

1. Скопируйте `.env.example` в `.env` и задайте безопасные пароли.
2. Выполните `docker compose up --build`.
3. Откройте UI: `http://localhost:3000`
4. API / Swagger: `http://localhost:8000/docs`

Учётная запись по умолчанию (из `.env`):

- email: `admin@example.com`
- password: `change-me`

## Что уже есть (0.3.0-alpha)

- Docker: API, PostgreSQL, Redis, MinIO, Qdrant, Frontend
- JWT-авторизация и первый пользователь
- Компании и строительные объекты с архивированием
- Document Engine: `BuilderDocument`, секции, переменные, DOCX/PDF/HTML
- Реестр шаблонов, импорт DOCX, версии документов
- Библиотека блоков договора
- База знаний + поиск через Knowledge Agent
- AI Core: Coordinator, Document / Knowledge / Memory / Task agents
- Задачи и корпоративная память
- Журнал событий
- Чат помощника в UI

Примеры запросов к помощнику:

- `сделай договор`
- `найди ГОСТ`
- `добавь задачу подписать акт`
- `запомни: гарантия всегда 24 месяца`

Подробности: [docs/ROADMAP.md](docs/ROADMAP.md), [docs/PROJECT.md](docs/PROJECT.md).
