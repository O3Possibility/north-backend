import os
import requests
from abc import ABC, abstractmethod

class BaseAdapter(ABC):
    @abstractmethod
    def complete(self, prompt: str, system_prompt: str = None, **kwargs) -> str:
        pass

class MistralAdapter(BaseAdapter):
    def __init__(self, model_name: str, api_key: str = None, **kwargs):
        self.model_name = model_name
        self.api_key = api_key or os.getenv("MISTRAL_API_KEY")
        self.url = kwargs.get("base_url") or kwargs.get("api_base") or "https://api.mistral.ai/v1/chat/completions"

    def complete(self, prompt: str, system_prompt: str = None, **kwargs) -> str:
        """
        Final fix for keyword arguments. 
        Catches 'system' if passed instead of 'system_prompt'.
        """
        if not self.api_key:
            return "Error: MISTRAL_API_KEY not set."

        # Logic to handle both 'system' and 'system_prompt'
        final_system = system_prompt or kwargs.get("system") or "You are NORTH."

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        data = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": final_system},
                {"role": "user", "content": prompt}
            ]
        }
        
        try:
            endpoint = self.url
            if "/chat/completions" not in endpoint:
                endpoint = endpoint.rstrip("/") + "/chat/completions"

            response = requests.post(endpoint, headers=headers, json=data, timeout=45)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            return f"Mistral Error: {str(e)}"

    def generate(self, *args, **kwargs):
        return self.complete(*args, **kwargs)

class OpenAIAdapter(BaseAdapter):
    def __init__(self, model_name: str, api_key: str = None, **kwargs):
        self.model_name = model_name
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.url = kwargs.get("base_url") or kwargs.get("api_base") or "https://api.openai.com/v1/chat/completions"

    def complete(self, prompt: str, system_prompt: str = None, **kwargs) -> str:
        final_system = system_prompt or kwargs.get("system") or "You are NORTH."
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        data = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": final_system},
                {"role": "user", "content": prompt}
            ]
        }
        try:
            response = requests.post(self.url, headers=headers, json=data)
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            return f"OpenAI Error: {str(e)}"

    def generate(self, *args, **kwargs):
        return self.complete(*args, **kwargs)
