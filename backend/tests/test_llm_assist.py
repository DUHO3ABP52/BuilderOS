from __future__ import annotations

from app.modules.ai.llm_assist import _parse_json_object, classify_intent_with_llm
from app.modules.ai.schemas import IntentName
from app.services import llm as llm_service
from app.services.llm import LLMEndpoint, active_endpoints


def test_parse_json_object_plain() -> None:
    data = _parse_json_object('{"intent":"search_knowledge","query":"ГОСТ 21"}')
    assert data == {"intent": "search_knowledge", "query": "ГОСТ 21"}


def test_parse_json_object_fenced() -> None:
    raw = 'Вот ответ:\n```json\n{"intent":"help","query":""}\n```'
    assert _parse_json_object(raw) == {"intent": "help", "query": ""}


def test_classify_intent_with_llm_uses_mock(monkeypatch) -> None:
    monkeypatch.setattr(llm_service, "llm_is_configured", lambda: True)

    def fake_chat(messages, **kwargs):
        return '{"intent":"search_knowledge","query":"требования к бетону"}'

    monkeypatch.setattr(llm_service, "chat", fake_chat)
    result = classify_intent_with_llm("какие требования к бетону в нормах?")
    assert result is not None
    assert result[0] == IntentName.SEARCH_KNOWLEDGE
    assert "бетон" in result[1].lower()


def test_classify_intent_with_llm_disabled(monkeypatch) -> None:
    monkeypatch.setattr(llm_service, "llm_is_configured", lambda: False)
    assert classify_intent_with_llm("что угодно") is None


def test_hybrid_endpoints(monkeypatch) -> None:
    monkeypatch.setattr(llm_service.settings, "llm_provider", "hybrid")
    monkeypatch.setattr(llm_service.settings, "llm_base_url", "http://ollama:11434")
    monkeypatch.setattr(llm_service.settings, "llm_model", "qwen2.5:7b")
    monkeypatch.setattr(llm_service.settings, "llm_fallback_base_url", "http://omniroute:20128")
    monkeypatch.setattr(llm_service.settings, "llm_fallback_model", "auto/cheap")
    endpoints = active_endpoints(allow_cloud=True)
    assert len(endpoints) == 2
    assert endpoints[0].name == "ollama"
    assert endpoints[1].name == "omniroute"
    assert isinstance(endpoints[1], LLMEndpoint)


def test_knowledge_blocks_cloud_by_default(monkeypatch) -> None:
    calls = []

    def fake_chat(messages, **kwargs):
        calls.append(kwargs.get("allow_cloud"))
        return "ok"

    monkeypatch.setattr(llm_service, "llm_is_configured", lambda: True)
    monkeypatch.setattr(llm_service, "chat", fake_chat)
    monkeypatch.setattr(llm_service.settings, "llm_cloud_for_knowledge", False)

    from app.modules.ai.llm_assist import synthesize_knowledge_answer
    from types import SimpleNamespace

    items = [SimpleNamespace(title="ГОСТ", category="gost", content="текст нормы")]
    synthesize_knowledge_answer("гарантия", items)
    assert calls == [False]
