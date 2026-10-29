"""
Vidhik Platform - Ollama LLM Provider Unit & Integration Tests
==============================================================
Validates:
1. Provider selection via environment configuration (LLM_PROVIDER=ollama).
2. Explicit factory instantiation via get_llm_provider("ollama").
3. Custom model and base URL configuration.
4. Provider name formatting.
5. Unknown provider fallback to OfflineMockLLMProvider.
6. Mocked request and response payload parsing.
7. Error handling for empty response or connection errors.
8. Live generation test with local Ollama server if available.
"""

import json
import asyncio
import urllib.request
import urllib.error
from io import BytesIO
from unittest.mock import patch, MagicMock
import pytest

from app.services.llm_provider import (
    BaseLLMProvider,
    LLMProviderConfigurationError,
    OllamaLLMProvider,
    OfflineMockLLMProvider,
    get_llm_provider
)


def test_get_llm_provider_ollama_env():
    """Asserts that get_llm_provider() selects OllamaLLMProvider when configured in environment."""
    with patch.dict("os.environ", {
        "LLM_PROVIDER": "ollama",
        "OLLAMA_MODEL": "llama3.2:3b",
        "OLLAMA_BASE_URL": "http://ollama.internal:11434",
    }):
        provider = get_llm_provider()
        assert isinstance(provider, OllamaLLMProvider)
        assert provider.provider_name == "ollama (llama3.2:3b)"


def test_get_llm_provider_explicit_arg():
    """Asserts that get_llm_provider('ollama') directly instantiates OllamaLLMProvider."""
    provider = get_llm_provider("ollama")
    assert isinstance(provider, OllamaLLMProvider)


def test_ollama_custom_model_and_url():
    """Asserts that custom model and base_url are respected."""
    with patch.dict("os.environ", {
        "OLLAMA_MODEL": "mistral:7b",
        "OLLAMA_BASE_URL": "http://127.0.0.1:11434"
    }):
        provider = OllamaLLMProvider()
        assert provider.model == "mistral:7b"
        assert provider.base_url == "http://127.0.0.1:11434"
        assert provider.provider_name == "ollama (mistral:7b)"


def test_unknown_provider_fallback():
    """An unknown provider fails clearly instead of silently selecting offline synthesis."""
    with patch.dict("os.environ", {"LLM_PROVIDER": "non_existent_provider_xyz"}):
        with pytest.raises(LLMProviderConfigurationError) as exc_info:
            get_llm_provider()
        assert exc_info.value.failure_category == "unsupported_provider"
        assert "non_existent_provider_xyz" not in str(exc_info.value)


def test_ollama_missing_base_url_is_a_sanitized_configuration_error(monkeypatch):
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    monkeypatch.setenv("OLLAMA_MODEL", "llama3.2:3b")

    with pytest.raises(LLMProviderConfigurationError) as exc_info:
        OllamaLLMProvider()

    assert exc_info.value.failure_category == "missing_ollama_base_url"
    assert "localhost" not in str(exc_info.value)


def test_ollama_loopback_url_is_rejected_on_render(monkeypatch):
    monkeypatch.setenv("RENDER", "true")
    monkeypatch.setenv("OLLAMA_MODEL", "llama3.2:3b")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")

    with pytest.raises(LLMProviderConfigurationError) as exc_info:
        get_llm_provider("ollama")

    assert exc_info.value.failure_category == "ollama_loopback_url_on_render"
    assert "localhost" not in str(exc_info.value)


def test_ollama_ipv4_loopback_range_is_rejected_on_render(monkeypatch):
    monkeypatch.setenv("RENDER", "true")
    monkeypatch.setenv("OLLAMA_MODEL", "llama3.2:3b")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://127.0.0.2:11434")

    with pytest.raises(LLMProviderConfigurationError) as exc_info:
        get_llm_provider("ollama")

    assert exc_info.value.failure_category == "ollama_loopback_url_on_render"


def test_render_missing_gemini_key_is_a_configuration_error(monkeypatch):
    monkeypatch.setenv("RENDER", "true")
    monkeypatch.setenv("GEMINI_API_KEY", "")
    monkeypatch.setenv("LLM_API_KEY", "")

    with pytest.raises(LLMProviderConfigurationError) as exc_info:
        get_llm_provider("gemini")

    assert exc_info.value.failure_category == "missing_gemini_api_key"
    assert str(exc_info.value) == "LLM provider configuration error (missing_gemini_api_key)."


def test_application_startup_remains_available_before_dependency_checks(monkeypatch):
    import app.main as main
    with patch.object(main, "close_db_pool") as close_pool:
        async def start_app():
            async with main.lifespan(main.app):
                pass

        asyncio.run(start_app())

    close_pool.assert_called_once()


def test_provider_readiness_reports_missing_config_without_secret_values(monkeypatch):
    from app.services.llm_provider import check_llm_provider_readiness

    monkeypatch.setenv("RENDER", "true")
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "")
    monkeypatch.setenv("LLM_API_KEY", "")
    result = check_llm_provider_readiness()
    assert result["ready"] is False
    assert result["failure_category"] == "missing_gemini_api_key"
    assert "sensitive" not in str(result)


def test_ollama_readiness_succeeds_when_configured_model_is_available(monkeypatch):
    from app.services.llm_provider import check_llm_provider_readiness

    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("OLLAMA_MODEL", "llama3.2:3b")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://ollama.internal:11434")
    ready = MagicMock()
    ready.read.return_value = b'{"models": [{"name": "llama3.2:3b"}]}'
    ready.__enter__.return_value = ready
    monkeypatch.setattr("urllib.request.urlopen", MagicMock(return_value=ready))
    result = check_llm_provider_readiness()
    assert result["ready"] is True
    assert result["provider"] == "ollama (llama3.2:3b)"


def test_ollama_readiness_reports_unreachable_provider_safely(monkeypatch):
    from app.services.llm_provider import check_llm_provider_readiness

    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("OLLAMA_MODEL", "llama3.2:3b")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://ollama.internal:11434")
    monkeypatch.delenv("RENDER", raising=False)
    monkeypatch.setattr("urllib.request.urlopen", MagicMock(side_effect=TimeoutError("sensitive url detail")))
    result = check_llm_provider_readiness()
    assert result["ready"] is False
    assert result["failure_category"] == "timeout"
    assert "sensitive" not in str(result)


def test_ollama_readiness_rejects_malformed_and_missing_model_responses(monkeypatch):
    from app.services.llm_provider import check_llm_provider_readiness

    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("OLLAMA_MODEL", "llama3.2:3b")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://ollama.internal:11434")
    malformed = MagicMock()
    malformed.read.return_value = b"not-json"
    malformed.__enter__.return_value = malformed
    monkeypatch.setattr("urllib.request.urlopen", MagicMock(return_value=malformed))
    result = check_llm_provider_readiness()
    assert result["ready"] is False
    assert result["failure_category"] == "malformed_response"

    valid_without_model = MagicMock()
    valid_without_model.read.return_value = b'{"models": []}'
    valid_without_model.__enter__.return_value = valid_without_model
    monkeypatch.setattr("urllib.request.urlopen", MagicMock(return_value=valid_without_model))
    result = check_llm_provider_readiness()
    assert result["ready"] is False
    assert result["failure_category"] == "model_not_available"


def test_liveness_is_fast_and_readiness_separates_dependencies():
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    live = client.get("/health")
    assert live.status_code == 200
    assert live.json()["status"] == "alive"
    assert live.json()["database"]["status"] == "not_checked"
    assert live.json()["llm_provider"]["status"] == "not_checked"

    with patch("app.routers.health.check_db_connection", return_value={"status": "connected"}), \
         patch("app.routers.health.check_llm_provider_readiness", return_value={"provider": "gemini (test-model)", "ready": False, "status": "not_ready", "failure_category": "timeout"}):
        not_ready = client.get("/health/ready")
    assert not_ready.status_code == 503
    assert not_ready.json()["database"]["status"] == "connected"
    assert not_ready.json()["llm_provider"]["failure_category"] == "timeout"


def test_provider_subsystem_health_reports_degraded_without_provider():
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    degraded = {"provider": None, "ready": False, "status": "configuration_error", "failure_category": "missing_api_key"}
    with patch("app.routers.assistant.check_llm_provider_readiness", return_value=degraded), \
         patch("app.routers.rag.check_llm_provider_readiness", return_value=degraded):
        assistant = client.get("/api/assistant/health")
        rag = client.get("/api/rag/health")
    assert assistant.status_code == rag.status_code == 503
    assert assistant.json()["status"] == rag.json()["status"] == "degraded"


def test_ollama_generate_mock_success():
    """Asserts that generate parses Ollama API JSON response structure correctly."""
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({
        "model": "llama3.2:3b",
        "message": {
            "role": "assistant",
            "content": "Section 73 provides compensation for breach of contract."
        },
        "done": True
    }).encode("utf-8")
    mock_response.__enter__.return_value = mock_response

    with patch("urllib.request.urlopen", return_value=mock_response):
        provider = OllamaLLMProvider(model="llama3.2:3b")
        res = provider.generate(
            prompt="What is Section 73?",
            system_instruction="You are a legal assistant."
        )
        assert "Section 73 provides compensation" in res


def test_ollama_generate_empty_response_raises():
    """An empty content response is classified without leaking provider payload."""
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({
        "model": "llama3.2:3b",
        "message": {"role": "assistant", "content": ""},
        "done": True
    }).encode("utf-8")
    mock_response.__enter__.return_value = mock_response

    with patch("urllib.request.urlopen", return_value=mock_response):
        provider = OllamaLLMProvider()
        with pytest.raises(RuntimeError, match="LLM provider request failed") as exc_info:
            provider.generate(prompt="Test", system_instruction="Test")
        assert exc_info.value.failure_category == "malformed_response"


def test_ollama_generate_connection_error():
    """Connection failures are classified without exposing transport details."""
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Connection refused")):
        provider = OllamaLLMProvider()
        with pytest.raises(RuntimeError, match="LLM provider request failed") as exc_info:
            provider.generate(prompt="Test", system_instruction="Test")
        assert exc_info.value.failure_category == "transport"


def test_ollama_timeout_is_classified_without_leaking_exception(monkeypatch):
    from app.services.llm_provider import LLMProviderError

    monkeypatch.setattr("urllib.request.urlopen", MagicMock(side_effect=TimeoutError("private timeout detail")))
    provider = OllamaLLMProvider(model="llama3.2:3b", base_url="http://127.0.0.1:11434")

    with pytest.raises(LLMProviderError) as exc_info:
        provider.generate(prompt="private prompt", system_instruction="private system prompt")

    assert exc_info.value.failure_category == "timeout"
    assert str(exc_info.value) == "LLM provider request failed."


def test_ollama_live_generation_if_running():
    """Validates live generation against local Ollama instance if active."""
    provider = OllamaLLMProvider()
    try:
        # Quick ping to check if Ollama is running
        req = urllib.request.Request(f"{provider.base_url}/api/tags")
        with urllib.request.urlopen(req, timeout=2) as resp:
            data = json.loads(resp.read().decode())
    except Exception:
        pytest.skip("Local Ollama instance not reachable on default port.")

    response = provider.generate(
        prompt="Reply with the single word: VERIFIED",
        system_instruction="Be strictly concise.",
        temperature=0.0,
        max_output_tokens=10
    )
    assert response and len(response.strip()) > 0
