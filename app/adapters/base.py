from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class ModelAdapter(ABC):

    @abstractmethod
    def complete(
        self,
        prompt: str,
        *,
        system: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 512,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        raise NotImplementedError


LLMAdapter = ModelAdapter
