# BuilderOS

Локальный цифровой сотрудник строительного ИП.

## Принципы

1. Объект строительства — центр рабочего контекста.
2. Данные и документы принадлежат компании и хранятся локально.
3. ИИ не подставляет вымышленные сведения и не публикует документы сам.
4. Каждое изменение документа версионируется и объясняется.
5. Документы собираются из блоков и шаблонов, а не генерируются «с нуля».

## Текущий контур (0.9.0-alpha)

- Auth, Companies, Projects, Documents, Templates, Blocks
- Knowledge + RAG (Qdrant)
- AI Core + локальная LLM
- Импорт образцов (DOCX/PDF/фото) → шаблон
- OCR: Tesseract + vision-LLM для сложных сканов
- Обучение Memory на правках шаблонов
- Knowledge graph связей объекта
- **Teacher**: обезличенный вопрос → облако → локальный PATTERN
- Финансы / календарь / задачи / audit / dashboard

Документация: [ROADMAP.md](ROADMAP.md), [LEARNING.md](LEARNING.md), [GRAPH.md](GRAPH.md), [RAG.md](RAG.md), [SAMPLES.md](SAMPLES.md), [LLM.md](LLM.md).
