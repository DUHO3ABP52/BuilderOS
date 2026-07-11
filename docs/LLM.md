# Локальная LLM и OmniRoute в BuilderOS

## Принцип

1. **Ollama** стартует вместе с `docker compose up` и **сама скачивает** модель (`ollama-init` + автопрогрев API).
2. Помощник в UI работает через `/api/v1/ai/ask`; LLM усиливает разбор фраз и ответы по знаниям.
3. Опционально — **[OmniRoute](https://github.com/diegosouzapw/OmniRoute)**: локальный gateway к 90+ бесплатным облачным моделям (`auto/cheap`), если локальная недоступна.

Документы по-прежнему только из шаблонов. Фрагменты базы знаний **по умолчанию не уходят в облако**.

## Режимы (`LLM_PROVIDER`)

| Режим | Поведение |
|---|---|
| `ollama` | Только локальная модель |
| `omniroute` | Только OmniRoute (`http://…:20128/v1`, модель `auto/cheap`) |
| `hybrid` | Сначала Ollama, при сбое — OmniRoute |

## Железо (локально)

| Железо | Модель |
|---|---|
| 8–12 GB VRAM / сильный CPU | `qwen2.5:7b` (по умолчанию) |
| 12–16 GB VRAM | `qwen2.5:14b` |
| 24 GB VRAM | `qwen2.5:32b` |

## Запуск «всё сразу»

```bash
docker compose up --build
```

Что происходит:
- поднимаются API, UI, Postgres, Redis, MinIO, Qdrant, **Ollama**;
- `ollama-init` делает `ollama pull qwen2.5:7b` (первый раз долго, потом из volume);
- API в фоне прогревает модель (короткий ping).

Проверка: `GET /api/v1/ai/llm-status` или в чате помощника — строка статуса LLM.

Отключить LLM: `LLM_ENABLED=false`.

## OmniRoute (бесплатные модели)

OmniRoute — **не облако BuilderOS**, а локальный прокси на вашей машине:  
`http://localhost:20128/v1` → маршрутизация по free-tier провайдерам.

### Вариант A — в составе BuilderOS

```bash
docker compose --profile omniroute up --build
```

Dashboard: http://localhost:20128  
В `.env` уже задано:

```env
LLM_PROVIDER=hybrid
LLM_FALLBACK_BASE_URL=http://omniroute:20128
LLM_FALLBACK_MODEL=auto/cheap
```

После первого старта откройте dashboard OmniRoute и подключите нужные free-провайдеры (ключи/OAuth по их инструкции).

### Вариант B — отдельно на хосте

```bash
docker run -d --name omniroute --restart unless-stopped \
  -p 20128:20128 -v omniroute-data:/app/data \
  diegosouzapw/omniroute:latest
```

В `.env` API-контейнера:

```env
LLM_FALLBACK_BASE_URL=http://host.docker.internal:20128
```

### Конфиденциальность

| Задача | Облако (OmniRoute) |
|---|---|
| Разбор намерения («что хочет пользователь») | допустимо в hybrid |
| Ответ по фрагментам ГОСТ/СП из вашей базы | **нет** по умолчанию (`LLM_CLOUD_FOR_KNOWLEDGE=false`) |

## GPU (NVIDIA)

```yaml
# у сервиса ollama
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: 1
          capabilities: [gpu]
```
