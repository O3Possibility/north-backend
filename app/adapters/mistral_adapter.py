import httpx

from app.adapters.base import LLMAdapter


class MistralAdapter(LLMAdapter):
    """Mistral chat-completions adapter using the OpenAI-compatible REST endpoint.

    Default base URL: https://api.mistral.ai/v1
    Endpoint: {base_url}/chat/completions
    """

    def __init__(
        self,
        api_key: str,
        model_name: str = "mistral-small-latest",
        base_url: str = "https://api.mistral.ai/v1",
        max_predict: int = 240,
        timeout_s: float = 60.0,
    ):
        self.api_key = (api_key or "").strip()
        self.model_name = (model_name or "mistral-small-latest").strip()
        self.base_url = (base_url or "https://api.mistral.ai/v1").rstrip("/")
        self.max_predict = int(max_predict)
        self.timeout_s = float(timeout_s)

    def generate(self, system: str, prompt: str) -> str:
        if not self.api_key:
            return (
                "[STATUS] REFUSAL\n"
                "[REPAIR/FEEDBACK]\nMissing Mistral API key. "
                "Set MISTRAL_API_KEY on the server or provide an api_key in the request."
            )

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": int(self.max_predict),
            "temperature": 0.2,
        }

        with httpx.Client(timeout=self.timeout_s) as client:
            r = client.post(url, headers=headers, json=payload)
            r.raise_for_status()
            data = r.json()

        # OpenAI-compatible response format
        try:
            return data["choices"][0]["message"]["content"]
        except Exception:
            return str(data)
