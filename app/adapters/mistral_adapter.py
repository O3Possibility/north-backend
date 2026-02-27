import os
import requests
from abc import ABC, abstractmethod

class BaseAdapter(ABC):
    @abstractmethod
    def complete(self, prompt: str, system_prompt: str = None, **kwargs) -> str:
        pass

class MistralAdapter(BaseAdapter):
    def __init__(self, model_name: str, api_key: str = None, **kwargs):
        self.model_name = (model_name or "open-mistral-7b").strip()
        self.api_key = api_key or os.getenv("MISTRAL_API_KEY") or os.getenv("OPENROUTER_API_KEY")
        
        provider = os.getenv("MODEL_PROVIDER", "mistral").lower()
        if "openrouter" in provider:
            self.url = "https://openrouter.ai/api/v1/chat/completions"
        else:
            self.url = "https://api.mistral.ai/v1/chat/completions"

    def complete(self, prompt: str, system_prompt: str = None, **kwargs) -> str:
        final_system = system_prompt or kwargs.get("system") or "You are NORTH."
        
        # Remove any accidental spaces or hidden characters from Render
        raw_key = "".join((self.api_key or "").split())
        
        if not raw_key:
            return "Error: API Key is missing."

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {raw_key}"
        }
        
        data = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": final_system},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7
        }
        
        try:
            response = requests.post(self.url, headers=headers, json=data, timeout=45)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            # Captures that 401 error you see in image_2a35fa.jpg
            return f"Model Error: {str(e)}"

    def generate(self, *args, **kwargs):
        return self.complete(*args, **kwargs)
