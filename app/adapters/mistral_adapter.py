import os
import requests
from abc import ABC, abstractmethod

class BaseAdapter(ABC):
    @abstractmethod
    def complete(self, prompt: str, system_prompt: str = None) -> str:
        pass

class MistralAdapter(BaseAdapter):
    # Added **kwargs to catch 'base_url' or other unexpected arguments
    def __init__(self, model_name: str, api_key: str = None, **kwargs):
        self.model_name = model_name
        self.api_key = api_key or os.getenv("MISTRAL_API_KEY")
        # Store base_url if provided, otherwise use default Mistral endpoint
        self.url = kwargs.get("base_url") or kwargs.get("api_base") or "https://api.mistral.ai/v1/chat/completions"

    def complete(self, prompt: str, system_prompt: str = None) -> str:
        if not self.api_key:
            return "Error: MISTRAL_API_KEY is missing from server environment."

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        data = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt or "You are NORTH."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7
        }
        
        try:
            # If the URL provided doesn't end in completions, append it
            request_url = self.url
            if not request_url.endswith("/chat/completions"):
                request_url = request_url.rstrip("/") + "/chat/completions"

            response = requests.post(request_url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            return f"Mistral API Error ({self.model_name}): {str(e)}"

class OpenAIAdapter(BaseAdapter):
    def __init__(self, model_name: str, api_key: str = None, **kwargs):
        self.model_name = model_name
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.url = kwargs.get("base_url") or kwargs.get("api_base") or "https://api.openai.com/v1/chat/completions"

    def complete(self, prompt: str, system_prompt: str = None) -> str:
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        data = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt or "You are NORTH."},
                {"role": "user", "content": prompt}
            ]
        }
        try:
            response = requests.post(self.url, headers=headers, json=data)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            return f"OpenAI API Error: {str(e)}"
