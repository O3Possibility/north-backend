import os
import requests
from abc import ABC, abstractmethod

class BaseAdapter(ABC):
    """
    The blueprint that mandates all adapters must have a 'complete' method.
    """
    @abstractmethod
    def complete(self, prompt: str, system_prompt: str = None) -> str:
        pass

class MistralAdapter(BaseAdapter):
    def __init__(self, model_name: str, api_key: str = None):
        self.model_name = model_name
        self.api_key = api_key or os.getenv("MISTRAL_API_KEY")

    def complete(self, prompt: str, system_prompt: str = None) -> str:
        """
        Implementation of the 'complete' method for Mistral API.
        This resolves the 'abstract class' instantiation error.
        """
        if not self.api_key:
            raise ValueError("Mistral API Key not found. Please set MISTRAL_API_KEY environment variable.")

        url = "https://api.mistral.ai/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        data = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt or "You are NORTH, a model-agnostic admissibility engine."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7
        }
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            return f"Mistral API Error: {str(e)}"

class OpenAIAdapter(BaseAdapter):
    """
    Adding this as a fallback in case your gate.py tries to use it.
    """
    def __init__(self, model_name: str, api_key: str = None):
        self.model_name = model_name
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")

    def complete(self, prompt: str, system_prompt: str = None) -> str:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt or "You are NORTH."},
                {"role": "user", "content": prompt}
            ]
        }
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
