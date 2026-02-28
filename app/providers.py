from app.config import settings
from app.adapters.mock_adapter import MockAdapter
from app.adapters.ollama_adapter import OllamaAdapter
from app.adapters.mistral_adapter import MistralAdapter

def get_adapter(
    model_override: str | None = None, # maps to model_choice in gate.py
    provider_override: str | None = None,
    api_key: str | None = None,
    model_name: str | None = None,
    api_base: str | None = None,
):
    # Normalize inputs
    choice = (model_override or "default").lower().strip()
    # Ensure provider_override isn't accidentally swallowing 'None' from gate.py
    provider = (provider_override or "").lower().strip()

    # Priority 1: If an API Key is present, we ASSUME Mistral (BYOK path)
    if api_key and api_key.strip():
        resolved = "mistral"
    # Priority 2: Explicit provider
    elif provider:
        resolved = provider
    # Priority 3: Choice (mistral/ollama/mock)
    elif choice != "default":
        resolved = choice
    # Priority 4: System default
    else:
        resolved = settings.MODEL_PROVIDER.lower().strip()

    if resolved == "mistral":
        # CRITICAL: If api_key is empty here, Mistral returns the 401 you see in your logs
        key = (api_key or settings.MISTRAL_API_KEY or "").strip()
        mdl = (model_name or settings.MISTRAL_MODEL or "mistral-small-latest").strip()
        base = (api_base or settings.MISTRAL_BASE_URL or "https://api.mistral.ai/v1").strip()
        
        return MistralAdapter(
            api_key=key, 
            model_name=mdl, 
            base_url=base, 
            max_predict=settings.MAX_PREDICT
        ), "mistral"

    if resolved == "ollama":
        return OllamaAdapter(settings.OLLAMA_MODEL, settings.MAX_PREDICT), "ollama"

    return MockAdapter(), "mock"
