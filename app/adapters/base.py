# app/adapters/base.py
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class ModelAdapter(ABC):
"""
Minimal interface all model adapters must implement.

Everything else should call `complete(...)` and receive a plain string.
"""

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


# Backwards/alternate name support (so other files can import either)
LLMAdapter = ModelAdapter
