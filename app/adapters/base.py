from abc import ABC, abstractmethod

class ModelAdapter(ABC):
    @abstractmethod
    def generate(self, system: str, prompt: str) -> str:
        raise NotImplementedError
