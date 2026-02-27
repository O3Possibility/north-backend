import os
import requests
from abc import ABC, abstractmethod

class BaseAdapter(ABC):
    @abstractmethod
    def complete(self, prompt: str, system_prompt: str = None, **kwargs) -> str:
        pass

class MistralAdapter(BaseAdapter):
    def __init__(self, model_name: str, api_key: str = None, **kwargs):
        # 1. Clean the model name from Render settings
        self.model_name = (model_name or "open-mistral-7b").strip()
        
        # 2. Grab the key
        self.api_key = api_key or os.getenv("MISTRAL_API_KEY") or os.getenv("OPENROUTER_API_KEY")
        
        # 3. SET THE ABSOLUTE URL (Fixes the 404 in image_341f1e.jpg)
        provider = os.getenv("MODEL_PROVIDER", "mistral").lower()
        if "openrouter" in provider:
            self.url = "https://openrouter.ai/api/v1/chat/completions"
        else:
            self.url = "https://api.mistral.ai/v1/chat/completions"

    def complete(self, prompt: str, system_prompt: str = None, **kwargs) -> str:
        final_system = system_prompt or kwargs.get("system") or "You are NORTH."
        raw_key = "".join((self.api_key or "").split())
        
        if not raw_key:
            return "Error: No API Key found."

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {raw_key}"
        }
        
        # OpenRouter identity headers
        if "openrouter" in self.url:
            headers["HTTP-Referer"] = "https://render.com"
            headers["X-Title"] = "NORTH Engine"

        data = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": final_system},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7
        }
        
        try:
            # We use the absolute URL defined in __init__
            response = requests.post(self.url, headers=headers, json=data, timeout=45)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            # This will now report the 401 (Balance) or 404 (URL) clearly
            return f"Model Error: {str(e)}"

    def generate(self, *args, **kwargs):
        return self.complete(*args, **kwargs)
