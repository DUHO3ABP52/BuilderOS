# Knowledge graph объекта

Объект строительства — центр контекста. Граф собирает связи вокруг `Project`.

## Что входит

**Авто (derived):**
- заказчик / подрядчик
- документы, задачи, платежи, события календаря
- факты Memory с `project_id`

**Ручные / AI (`graph_edges`):**
- `related_to`, `mentions`, `depends_on`
- подпись, confidence, source (`manual` | `ai`)

## API

- `GET /api/v1/graph/projects/{id}` — полный граф
- `GET /api/v1/graph/projects/{id}/edges` — только ручные рёбра
- `POST /api/v1/graph/edges` — добавить связь
- `POST /api/v1/graph/edges/{id}/archive`

## ИИ

Запросы: «контекст объекта», «что связано с объектом», «граф».
Нужен `project_id` или однозначное имя объекта в фразе.
