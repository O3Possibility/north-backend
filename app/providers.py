from app.config import settings
from app.adapters.mock_adapter import MockAdapter
from app.adapters.ollama_adapter import OllamaAdapter
from app.adapters.mistral_adapter import MistralAdapter


def get_adapter(
    model_override: str | None = None,
    provider_override: str | None = None,
    api_key: str | None = None,
    model_name: str | None = None,
    api_base: str | None = None,
):
    """Return (adapter, provider_used).

    - model_override (legacy): 'default' | 'ollama' | 'mock' | 'mistral'
    - provider_override: explicit provider selection (preferred)
    - api_key/model_name/api_base: per-request overrides (BYOK / custom endpoint)
    """

    choice = (model_override or "default").lower().strip()
    provider = (provider_override or "").lower().strip()

    # Provider resolution
    if provider:
        resolved = provider
    elif choice != "default":
        resolved = choice
    else:
        resolved = settings.MODEL_PROVIDER.lower().strip()

    if resolved == "ollama":
        return OllamaAdapter(settings.OLLAMA_MODEL, settings.MAX_PREDICT), "ollama"

    if resolved == "mistral":
        key = (api_key or settings.MISTRAL_API_KEY or "").strip()
        mdl = (model_name or settings.MISTRAL_MODEL or "mistral-small-latest").strip()
        base = (api_base or settings.MISTRAL_BASE_URL or "https://api.mistral.ai/v1").strip()
        return MistralAdapter(key, mdl, base_url=base, max_predict=settings.MAX_PREDICT), "mistral"

    if resolved == "mock":
        return MockAdapter(), "mock"

    # fallback
    return MockAdapter(), "mock"
