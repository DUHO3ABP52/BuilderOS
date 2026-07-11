from app.modules.documents.engine.builder_document import BuilderDocument, BuilderSection
from app.modules.documents.engine.renderer import export_docx, export_html, export_pdf
from app.modules.documents.engine.variables import render_document


def test_render_and_export_document() -> None:
    document = BuilderDocument(
        title="Договор",
        doc_type="contract",
        sections=[
            BuilderSection(
                title="Стоимость",
                section_type="price",
                content="Сумма: {{contract.price}} руб. Заказчик: {{customer.name}}",
            )
        ],
        variables={"contract": {"price": 1000}, "customer": {"name": "ООО Тест"}},
    )
    rendered = render_document(document)
    assert "1000" in rendered.sections[0].content
    assert "ООО Тест" in rendered.sections[0].content
    assert export_docx(document)
    assert export_pdf(document).startswith(b"%PDF")
    assert "<h1>Договор</h1>" in export_html(document)
