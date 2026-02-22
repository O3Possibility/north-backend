# app/adapters/base.py
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class LLMAdapter(ABC):
"""
Minimal interface all model adapters must implement.
The rest of NORTH should only call .complete(...) on this.
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
