from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.blocks.models import BlockType, DocumentBlock
from app.modules.documents.engine.builder_document import BuilderDocument, BuilderSection, VariableDefinition
from app.modules.knowledge.models import KnowledgeCategory, KnowledgeItem
from app.modules.templates.models import DocumentTemplate, TemplateCategory

DEFAULT_BLOCKS = [
    {
        "slug": "header",
        "title": "Шапка",
        "block_type": BlockType.HEADER,
        "content": "ДОГОВОР № {{contract.number}}\nг. {{project.city}}\n{{contract.date}}",
    },
    {
        "slug": "subject",
        "title": "Предмет договора",
        "block_type": BlockType.SUBJECT,
        "content": (
            "1.1. Подрядчик обязуется выполнить работы по объекту «{{project.name}}» "
            "по адресу: {{project.address}}, а Заказчик обязуется принять результат и оплатить его."
        ),
    },
    {
        "slug": "price",
        "title": "Стоимость",
        "block_type": BlockType.PRICE,
        "content": "2.1. Стоимость работ составляет {{contract.price}} руб.",
    },
    {
        "slug": "responsibility",
        "title": "Ответственность",
        "block_type": BlockType.RESPONSIBILITY,
        "content": "3.1. Стороны несут ответственность в соответствии с законодательством РФ.",
    },
    {
        "slug": "payment",
        "title": "Порядок оплаты",
        "block_type": BlockType.PAYMENT,
        "content": "4.1. Оплата производится на основании актов выполненных работ.",
    },
    {
        "slug": "force-majeure",
        "title": "Форс-мажор",
        "block_type": BlockType.FORCE_MAJEURE,
        "content": "5.1. Стороны освобождаются от ответственности при наступлении обстоятельств непреодолимой силы.",
    },
    {
        "slug": "guarantee",
        "title": "Гарантии",
        "block_type": BlockType.GUARANTEE,
        "content": "6.1. Подрядчик предоставляет гарантию на выполненные работы сроком {{contract.guarantee_months}} месяцев.",
    },
    {
        "slug": "disputes",
        "title": "Споры",
        "block_type": BlockType.DISPUTES,
        "content": "7.1. Споры разрешаются путем переговоров, а при недостижении согласия — в суде по месту нахождения Подрядчика.",
    },
    {
        "slug": "appendix",
        "title": "Приложения",
        "block_type": BlockType.APPENDIX,
        "content": "Приложение №1 — Смета\nПриложение №2 — График производства работ",
    },
    {
        "slug": "signatures",
        "title": "Подписи",
        "block_type": BlockType.SIGNATURES,
        "content": (
            "Заказчик: {{customer.name}}, ИНН {{customer.inn}}\n"
            "Подрядчик: {{contractor.name}}, ИНН {{contractor.inn}}"
        ),
    },
]

DEFAULT_KNOWLEDGE = [
    {
        "title": "СП 48.13330 Организация строительства",
        "category": KnowledgeCategory.SP,
        "content": (
            "Организация строительного производства должна обеспечивать выполнение работ "
            "в сроки, предусмотренные договором, с соблюдением требований безопасности и качества. "
            "Подрядчик обязан вести исполнительную документацию и своевременно уведомлять заказчика "
            "о рисках срыва сроков."
        ),
    },
    {
        "title": "ГОСТ Р 21.101 Правила оформления проектной документации",
        "category": KnowledgeCategory.GOST,
        "content": (
            "Проектная документация должна иметь единую структуру, обозначения и комплектность. "
            "Изменения вносятся с фиксацией версии и основания. Каждый лист комплекта должен "
            "содержать обозначение документа и сведения об изменении."
        ),
    },
    {
        "title": "КС-2 и КС-3 — типовой порядок",
        "category": KnowledgeCategory.INTERNAL,
        "content": (
            "КС-2 фиксирует выполненные работы за период. КС-3 суммирует стоимость. "
            "Перед подписанием сверяются объёмы, расценки и приложения к договору. "
            "Без подписанной КС-2 закрытие периода не выполняется."
        ),
    },
    {
        "title": "СП 70.13330 Несущие и ограждающие конструкции",
        "category": KnowledgeCategory.SP,
        "content": (
            "Работы по устройству несущих и ограждающих конструкций выполняются по проекту "
            "производства работ. Контроль качества включает входной контроль материалов, "
            "операционный контроль и приёмку скрытых работ."
        ),
    },
    {
        "title": "Гарантийные обязательства подрядчика",
        "category": KnowledgeCategory.INTERNAL,
        "content": (
            "Типовая практика BuilderOS: гарантийный срок на общестроительные работы — 24 месяца "
            "с даты подписания акта приёмки, если договором не установлено иное. "
            "Гарантийные случаи фиксируются актом осмотра с фотофиксацией."
        ),
    },
]


def seed_default_blocks(session: Session) -> None:
    for item in DEFAULT_BLOCKS:
        exists = session.scalar(select(DocumentBlock.id).where(DocumentBlock.slug == item["slug"]).limit(1))
        if exists:
            continue
        session.add(DocumentBlock(**item))
    session.flush()
    _seed_default_contract_template(session)
    _seed_default_knowledge(session)


def _seed_default_knowledge(session: Session) -> None:
    for item in DEFAULT_KNOWLEDGE:
        exists = session.scalar(select(KnowledgeItem.id).where(KnowledgeItem.title == item["title"]).limit(1))
        if exists:
            continue
        session.add(
            KnowledgeItem(
                title=item["title"],
                category=item["category"].value,
                source_type="text",
                content=item["content"],
                source_metadata={"source": "system-seed"},
            )
        )
    session.flush()


def _seed_default_contract_template(session: Session) -> None:
    exists = session.scalar(
        select(DocumentTemplate.id).where(DocumentTemplate.slug == "dogovor-podryada").limit(1)
    )
    if exists:
        return

    blocks = {
        block.slug: block
        for block in session.scalars(select(DocumentBlock).where(DocumentBlock.is_archived.is_(False)))
    }
    section_slugs = [
        "header",
        "subject",
        "price",
        "payment",
        "responsibility",
        "guarantee",
        "force-majeure",
        "disputes",
        "appendix",
        "signatures",
    ]
    sections = [
        BuilderSection(
            title=blocks[slug].title,
            section_type=blocks[slug].block_type,
            content=blocks[slug].content,
        )
        for slug in section_slugs
        if slug in blocks
    ]
    content = BuilderDocument(
        title="Договор подряда",
        doc_type="contract",
        sections=sections,
        variables={},
        metadata={"source": "system-seed"},
    )
    variables = [
        VariableDefinition(key="customer.name", var_type="string", required=True, label="Заказчик"),
        VariableDefinition(key="customer.inn", var_type="inn", required=True, label="ИНН заказчика"),
        VariableDefinition(key="contractor.name", var_type="string", required=True, label="Подрядчик"),
        VariableDefinition(key="contractor.inn", var_type="inn", required=True, label="ИНН подрядчика"),
        VariableDefinition(key="project.name", var_type="string", required=True, label="Объект"),
        VariableDefinition(key="project.address", var_type="string", required=True, label="Адрес объекта"),
        VariableDefinition(key="project.city", var_type="string", required=False, label="Город"),
        VariableDefinition(key="contract.number", var_type="string", required=True, label="Номер договора"),
        VariableDefinition(key="contract.date", var_type="date", required=True, label="Дата договора"),
        VariableDefinition(key="contract.price", var_type="float", required=True, label="Стоимость"),
        VariableDefinition(key="contract.guarantee_months", var_type="float", required=False, label="Гарантия, мес."),
    ]
    session.add(
        DocumentTemplate(
            name="Договор подряда",
            slug="dogovor-podryada",
            category=TemplateCategory.CONTRACT.value,
            version=1,
            content=content.model_dump(),
            variables=[item.model_dump() for item in variables],
            description="Базовый шаблон договора подряда из библиотеки блоков BuilderOS",
        )
    )
    session.flush()
