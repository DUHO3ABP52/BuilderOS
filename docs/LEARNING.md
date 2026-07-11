# Обучение и «саморазвитие» BuilderOS

## Что НЕ делает локальная LLM

Веса модели Ollama **не дообучаются** во время работы. Это нормально:
continuous fine-tuning тяжёлый, нестабильный и рискованный для ИП.

## Что делает система вокруг модели

| Механизм | Где | Эффект |
|---|---|---|
| Память фактов | Memory + «запомни» | Помнит предпочтения и факты |
| Diff шаблонов | версии шаблонов | PATTERN / TEMPLATE_HINT |
| RAG по нормам | Knowledge + Qdrant | Ответы по ГОСТ/СП |
| Knowledge graph | Graph | Связи заказчик↔документы↔платежи |
| **Teacher** | OmniRoute → Memory | Обезличенный вопрос → локальный PATTERN |
| Hybrid LLM | Ollama → OmniRoute | Помощь в разборе фраз |

Умнеет **контекст**, а не нейросеть сама по себе.

## Teacher-контур (Alpha 0.9)

1. Пользователь: `спроси учителя: как обычно формулируют гарантию`.
2. Система **обезличивает** текст (ИНН, суммы, ООО…, email, телефоны).
3. Вопрос уходит в **OmniRoute** (не в локальную Ollama).
4. Ответ показывается; PATTERN сохраняется только с `confirm=true`
   (или `LLM_TEACHER_AUTO_SAVE=true`).
5. Документы по-прежнему только из шаблонов — учитель не создаёт договор.

### API

- `POST /api/v1/ai/ask` с intent `ask_teacher`
- `POST /api/v1/ai/teacher/preview` — посмотреть sanitized вопрос
- `POST /api/v1/ai/teacher/ask` — прямой вызов (`save=true` чтобы записать)

### Env

```env
LLM_TEACHER_ENABLED=true
LLM_CLOUD_FOR_TEACHER=true
LLM_TEACHER_AUTO_SAVE=false
LLM_FALLBACK_BASE_URL=http://omniroute:20128
```

Запуск gateway: `docker compose --profile omniroute up --build`

### Приватность

| Данные | В облако |
|---|---|
| Обезличенный общий вопрос | да (учитель) |
| ИНН / суммы / сканы / адреса | нет (редятся) |
| Фрагменты вашей базы знаний | нет по умолчанию |
| Vision OCR сканов | нет по умолчанию |
