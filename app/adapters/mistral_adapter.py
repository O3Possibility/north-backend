import os
import requests
from .base import BaseAdapter # Points to your base.py file

class MistralAdapter(BaseAdapter):
    def __init__(self, model_name: str, api_key: str = None, **kwargs):
        self.model_name = model_name
        # Grabs the key; supports OpenRouter fallback
        self.api_key = api_key or os.getenv("MISTRAL_API_KEY") or os.getenv("OPENROUTER_API_KEY")
        
        # Check if we are using OpenRouter based on your Render settings
        provider = os.getenv("MODEL_PROVIDER", "mistral").lower()
        if "openrouter" in provider:
            self.url = "https://openrouter.ai/api/v1/chat/completions"
        else:
            self.url = kwargs.get("base_url") or "https://api.mistral.ai/v1/chat/completions"

    def complete(self, prompt: str, system_prompt: str = None, **kwargs) -> str:
        # Prevents the NameError: final_system is not defined
        final_system = system_prompt or kwargs.get("system") or "You are NORTH."
        
        # Clean the key of all whitespace/newlines
        raw_key = "".join((self.api_key or "").split())
        
        if not raw_key:
            return "Error: No API Key found in Environment Variables."

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {raw_key}"
        }
        
        # OpenRouter specific requirements
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
            response = requests.post(self.url, headers=headers, json=data, timeout=45)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            return f"Adapter Error: {str(e)}"

    # Alias for gate.py compatibility
    def generate(self, *args, **kwargs):
        return self.complete(*args, **kwargs)
