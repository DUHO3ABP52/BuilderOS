# BuilderOS

Локальный цифровой сотрудник строительного ИП.

## Принципы

1. Объект строительства — центр рабочего контекста.
2. Данные и документы принадлежат компании и хранятся локально.
3. ИИ не подставляет вымышленные сведения и не публикует документы сам.
4. Каждое изменение документа версионируется и объясняется.
5. Документы собираются из блоков и шаблонов, а не генерируются «с нуля».

## Текущий контур (0.4.0-alpha)

- Auth + Users
- Companies / Projects
- Document Engine (BuilderDocument, templates, blocks, export)
- Knowledge registry + **RAG (Qdrant)**
- AI Core: Coordinator + Document / Knowledge / Memory / Task agents
- Tasks + Memory facts
- Audit events
- Web dashboard + чат помощника
- Локальная LLM (Ollama) + опциональный OmniRoute

## AI / RAG

- `POST /api/v1/ai/ask` — помощник
- `GET /api/v1/ai/llm-status` — статус LLM
- `GET /api/v1/knowledge/search?q=` — семантический + лексический поиск
- `POST /api/v1/knowledge/reindex` — переиндексация Qdrant

Подробности: [LLM.md](LLM.md), [RAG.md](RAG.md).
