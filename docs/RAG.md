# RAG в BuilderOS

## Цель Alpha 0.4

Семантический поиск по базе знаний (СП / ГОСТ / внутренние нормы) через Qdrant.

## Как работает

1. Запись knowledge режется на чанки.
2. Для каждого чанка строится embedding (`nomic-embed-text` через Ollama).
3. Чанки пишутся в коллекцию Qdrant `builderos_knowledge`.
4. Knowledge Agent сначала ищет в Qdrant, затем дополняет лексическим ILIKE.
5. При недоступности Ollama/Qdrant используется локальный fallback-эмбеддинг и in-memory индекс.

## API

- `GET /api/v1/knowledge/search?q=...`
- `GET /api/v1/knowledge/rag-status`
- `POST /api/v1/knowledge/reindex`

## Запуск

```bash
docker compose up --build
```

`ollama-init` скачает и chat-модель, и `nomic-embed-text`.
После старта API фоном переиндексирует знания.

Отключить RAG: `RAG_ENABLED=false`.
