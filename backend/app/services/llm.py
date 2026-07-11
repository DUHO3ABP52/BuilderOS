from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Ошибка вызова LLM."""


@dataclass(frozen=True)
class LLMEndpoint:
    name: str
    base_url: str
    model: str
    api_key: str | None = None
    kind: str = "openai"  # openai | ollama


_warm_lock = threading.Lock()
_warm_started = False
_warm_state = {"ready": False, "detail": "not_started", "endpoint": None}


def llm_is_configured() -> bool:
    return bool(settings.llm_enabled and settings.llm_model and settings.llm_base_url)


def _normalize_base(url: str) -> str:
    return url.rstrip("/")


def primary_endpoint() -> LLMEndpoint:
    provider = (settings.llm_provider or "ollama").strip().lower()
    kind = "ollama" if provider in {"ollama", "hybrid"} and "11434" in settings.llm_base_url else "openai"
    if provider == "omniroute":
        kind = "openai"
    return LLMEndpoint(
        name=provider if provider != "hybrid" else "ollama",
        base_url=_normalize_base(settings.llm_base_url),
        model=settings.llm_model,
        api_key=settings.llm_api_key or None,
        kind=kind,
    )


def fallback_endpoint() -> LLMEndpoint | None:
    provider = (settings.llm_provider or "ollama").strip().lower()
    if provider == "omniroute":
        return None
    if provider == "hybrid" or settings.llm_fallback_base_url:
        base = settings.llm_fallback_base_url or "http://omniroute:20128"
        model = settings.llm_fallback_model or "auto/cheap"
        return LLMEndpoint(
            name="omniroute",
            base_url=_normalize_base(base),
            model=model,
            api_key=settings.llm_fallback_api_key or settings.llm_api_key or None,
            kind="openai",
        )
    return None


def vision_endpoint() -> LLMEndpoint:
    """Локальная vision-модель на том же OpenAI-compatible endpoint (обычно Ollama)."""
    base = _normalize_base(settings.llm_base_url)
    kind = "ollama" if ":11434" in base else "openai"
    return LLMEndpoint(
        name="vision",
        base_url=base,
        model=settings.llm_vision_model,
        api_key=settings.llm_api_key or None,
        kind=kind,
    )


def vision_endpoints(*, allow_cloud: bool = False) -> list[LLMEndpoint]:
    endpoints = [vision_endpoint()]
    if allow_cloud and settings.llm_cloud_for_vision:
        fb = fallback_endpoint()
        if fb:
            endpoints.append(
                LLMEndpoint(
                    name=f"{fb.name}-vision",
                    base_url=fb.base_url,
                    model=settings.llm_vision_model or fb.model,
                    api_key=fb.api_key,
                    kind=fb.kind,
                )
            )
    return endpoints


def active_endpoints(*, allow_cloud: bool = True) -> list[LLMEndpoint]:
    provider = (settings.llm_provider or "ollama").strip().lower()
    primary = primary_endpoint()
    if provider == "omniroute":
        return [
            LLMEndpoint(
                name="omniroute",
                base_url=_normalize_base(settings.llm_base_url),
                model=settings.llm_model or "auto/cheap",
                api_key=settings.llm_api_key or None,
                kind="openai",
            )
        ]
    endpoints = [primary]
    if allow_cloud:
        fb = fallback_endpoint()
        if fb and provider == "hybrid":
            endpoints.append(fb)
        elif fb and settings.llm_fallback_base_url and provider == "ollama":
            # явный fallback даже при provider=ollama, если задан URL
            endpoints.append(fb)
    return endpoints


def _headers(endpoint: LLMEndpoint) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if endpoint.api_key:
        headers["Authorization"] = f"Bearer {endpoint.api_key}"
    return headers


def _chat_url(endpoint: LLMEndpoint) -> str:
    return f"{endpoint.base_url}/v1/chat/completions"


def _models_url(endpoint: LLMEndpoint) -> str:
    return f"{endpoint.base_url}/v1/models"


def _tags_url(endpoint: LLMEndpoint) -> str:
    return f"{endpoint.base_url}/api/tags"


def _pull_url(endpoint: LLMEndpoint) -> str:
    return f"{endpoint.base_url}/api/pull"


def check_endpoint(endpoint: LLMEndpoint, timeout: float = 2.0) -> str:
    try:
        with httpx.Client(timeout=timeout) as client:
            if endpoint.kind == "ollama" or ":11434" in endpoint.base_url:
                response = client.get(_tags_url(endpoint))
                if response.status_code == 200:
                    return "ok"
            response = client.get(_models_url(endpoint), headers=_headers(endpoint))
            return "ok" if response.status_code == 200 else "unavailable"
    except Exception:
        return "unavailable"


def check_llm() -> str:
    if not settings.llm_enabled:
        return "disabled"
    statuses = [check_endpoint(ep) for ep in active_endpoints(allow_cloud=True)]
    if any(status == "ok" for status in statuses):
        return "ok"
    return "unavailable"


def list_models(endpoint: LLMEndpoint | None = None) -> list[str]:
    endpoint = endpoint or primary_endpoint()
    try:
        with httpx.Client(timeout=3.0) as client:
            if endpoint.kind == "ollama" or ":11434" in endpoint.base_url:
                response = client.get(_tags_url(endpoint))
                if response.status_code == 200:
                    models = response.json().get("models") or []
                    return [str(item.get("name", "")) for item in models if item.get("name")]
            response = client.get(_models_url(endpoint), headers=_headers(endpoint))
            if response.status_code == 200:
                data = response.json().get("data") or []
                return [str(item.get("id", "")) for item in data if item.get("id")]
    except Exception:
        return []
    return []


def model_is_ready(endpoint: LLMEndpoint | None = None) -> bool:
    endpoint = endpoint or primary_endpoint()
    names = list_models(endpoint)
    target = endpoint.model
    if target in names:
        return True
    return any(
        name == target or name.startswith(f"{target}-") or name.startswith(f"{target}:") or target in name
        for name in names
    )


def ensure_ollama_model(endpoint: LLMEndpoint | None = None) -> bool:
    """Скачивает модель в Ollama, если её ещё нет."""
    endpoint = endpoint or primary_endpoint()
    if endpoint.kind != "ollama" and ":11434" not in endpoint.base_url:
        return model_is_ready(endpoint)
    if model_is_ready(endpoint):
        return True
    logger.info("Pulling Ollama model %s ...", endpoint.model)
    try:
        with httpx.Client(timeout=None) as client:
            with client.stream(
                "POST",
                _pull_url(endpoint),
                json={"name": endpoint.model, "stream": False},
                timeout=httpx.Timeout(None, connect=10.0),
            ) as response:
                response.raise_for_status()
                for _ in response.iter_bytes():
                    pass
        return model_is_ready(endpoint)
    except Exception as exc:
        logger.warning("Ollama pull failed: %s", exc)
        return False


def chat(
    messages: list[dict[str, str]],
    *,
    temperature: float | None = None,
    max_tokens: int | None = None,
    allow_cloud: bool = True,
) -> str:
    if not llm_is_configured():
        raise LLMError("LLM отключена в настройках")

    payload_base: dict[str, Any] = {
        "temperature": settings.llm_temperature if temperature is None else temperature,
        "max_tokens": settings.llm_max_tokens if max_tokens is None else max_tokens,
        "stream": False,
    }

    errors: list[str] = []
    for endpoint in active_endpoints(allow_cloud=allow_cloud):
        payload = {**payload_base, "model": endpoint.model, "messages": messages}
        try:
            with httpx.Client(timeout=settings.llm_timeout_seconds) as client:
                response = client.post(_chat_url(endpoint), json=payload, headers=_headers(endpoint))
                response.raise_for_status()
                data = response.json()
            content = data["choices"][0]["message"]["content"]
            if not isinstance(content, str) or not content.strip():
                raise LLMError("Пустой ответ LLM")
            _warm_state["ready"] = True
            _warm_state["endpoint"] = endpoint.name
            _warm_state["detail"] = "ok"
            return content.strip()
        except Exception as exc:
            logger.warning("LLM %s failed: %s", endpoint.name, exc)
            errors.append(f"{endpoint.name}: {exc}")

    raise LLMError("Не удалось обратиться к LLM: " + "; ".join(errors))


def chat_vision(
    messages: list[dict[str, Any]],
    *,
    temperature: float = 0.0,
    max_tokens: int | None = None,
    allow_cloud: bool = False,
) -> str:
    """Multimodal chat (OCR/vision). По умолчанию только локальная модель."""
    if not settings.llm_vision_enabled:
        raise LLMError("Vision OCR отключён")
    if not llm_is_configured():
        raise LLMError("LLM отключена в настройках")

    payload_base: dict[str, Any] = {
        "temperature": temperature,
        "max_tokens": settings.llm_vision_max_tokens if max_tokens is None else max_tokens,
        "stream": False,
    }
    timeout = settings.llm_vision_timeout_seconds
    errors: list[str] = []
    for endpoint in vision_endpoints(allow_cloud=allow_cloud):
        if settings.llm_vision_auto_pull and (endpoint.kind == "ollama" or ":11434" in endpoint.base_url):
            ensure_ollama_model(endpoint)
        payload = {**payload_base, "model": endpoint.model, "messages": messages}
        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.post(_chat_url(endpoint), json=payload, headers=_headers(endpoint))
                response.raise_for_status()
                data = response.json()
            content = data["choices"][0]["message"]["content"]
            if not isinstance(content, str) or not content.strip():
                raise LLMError("Пустой ответ vision-LLM")
            return content.strip()
        except Exception as exc:
            logger.warning("Vision LLM %s failed: %s", endpoint.name, exc)
            errors.append(f"{endpoint.name}: {exc}")

    raise LLMError("Не удалось обратиться к vision-LLM: " + "; ".join(errors))


def warm_state() -> dict[str, Any]:
    return dict(_warm_state)


def start_llm_warmup_background() -> None:
    """Прогрев при старте API: pull модели + короткий ping (не блокирует lifespan)."""
    global _warm_started
    with _warm_lock:
        if _warm_started or not settings.llm_enabled:
            return
        _warm_started = True

    def _run() -> None:
        _warm_state["detail"] = "warming"
        provider = (settings.llm_provider or "ollama").strip().lower()
        if provider in {"ollama", "hybrid"}:
            for attempt in range(60):
                if check_endpoint(primary_endpoint()) == "ok":
                    break
                time.sleep(2)
                _warm_state["detail"] = f"waiting_ollama:{attempt}"
            else:
                _warm_state["detail"] = "ollama_unavailable"
                if provider == "ollama":
                    return

            if settings.llm_auto_pull:
                ok = ensure_ollama_model(primary_endpoint())
                if not ok and provider == "ollama":
                    _warm_state["detail"] = "pull_failed"
                    return

            try:
                chat(
                    [{"role": "user", "content": "ok"}],
                    temperature=0.0,
                    max_tokens=4,
                    allow_cloud=False,
                )
                _warm_state["ready"] = True
                _warm_state["detail"] = "local_ready"
                _warm_state["endpoint"] = "ollama"
                return
            except LLMError as exc:
                logger.info("Local warm-up skipped: %s", exc)
                _warm_state["detail"] = f"local_warm_failed:{exc}"

        if provider in {"omniroute", "hybrid"}:
            ep = (
                primary_endpoint()
                if provider == "omniroute"
                else fallback_endpoint() or primary_endpoint()
            )
            if check_endpoint(ep) == "ok":
                try:
                    chat(
                        [{"role": "user", "content": "ok"}],
                        temperature=0.0,
                        max_tokens=4,
                        allow_cloud=True,
                    )
                    _warm_state["ready"] = True
                    _warm_state["detail"] = "cloud_ready"
                    _warm_state["endpoint"] = ep.name
                except LLMError as exc:
                    _warm_state["detail"] = f"cloud_warm_failed:{exc}"
            else:
                _warm_state["detail"] = "cloud_unavailable"

    threading.Thread(target=_run, name="llm-warmup", daemon=True).start()


def status_payload() -> dict[str, Any]:
    endpoints = []
    for ep in active_endpoints(allow_cloud=True):
        st = check_endpoint(ep)
        endpoints.append(
            {
                "name": ep.name,
                "base_url": ep.base_url,
                "model": ep.model,
                "status": st,
                "model_ready": model_is_ready(ep) if st == "ok" else False,
                "models": list_models(ep) if st == "ok" else [],
            }
        )
    vision = None
    if settings.llm_vision_enabled:
        vep = vision_endpoint()
        vst = check_endpoint(vep)
        vision = {
            "enabled": True,
            "model": vep.model,
            "base_url": vep.base_url,
            "status": vst,
            "model_ready": model_is_ready(vep) if vst == "ok" else False,
            "cloud_allowed": settings.llm_cloud_for_vision,
        }
    else:
        vision = {"enabled": False, "model": settings.llm_vision_model, "status": "disabled"}
    return {
        "enabled": settings.llm_enabled,
        "provider": settings.llm_provider,
        "provider_status": check_llm(),
        "base_url": settings.llm_base_url,
        "model": settings.llm_model,
        "model_ready": any(item["model_ready"] for item in endpoints),
        "warmup": warm_state(),
        "endpoints": endpoints,
        "models": endpoints[0]["models"] if endpoints else [],
        "vision": vision,
    }
