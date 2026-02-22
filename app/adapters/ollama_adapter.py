import ollama
from app.adapters.base import ModelAdapter

class OllamaAdapter(ModelAdapter):
    def __init__(self, model_name: str, max_predict: int = 240):
        self.model_name = model_name
        self.max_predict = max_predict

    def generate(self, system: str, prompt: str) -> str:
        resp = ollama.generate(
            model=self.model_name,
            system=system,
            prompt=prompt,
            options={"num_predict": int(self.max_predict)}
        )
        return resp.get("response", "")
