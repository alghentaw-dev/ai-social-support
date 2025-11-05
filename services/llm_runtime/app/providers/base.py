from abc import ABC, abstractmethod
from typing import Dict, Iterable, Tuple

class BaseProvider(ABC):
    name: str

    @abstractmethod
    def generate(self, *, model: str, prompt: str, system: str | None,
                 options: Dict[str, str], json_mode: bool,
                 json_schema: str | None, max_tokens: int | None,
                 temperature: float | None, timeout_ms: int | None) -> Tuple[str, str]:
        """Return (text, finish_reason)."""

    @abstractmethod
    def generate_stream(self, *, model: str, prompt: str, system: str | None,
                        options: Dict[str, str], json_mode: bool,
                        json_schema: str | None, max_tokens: int | None,
                        temperature: float | None, timeout_ms: int | None) -> Iterable[Tuple[str, bool, str]]:
        """Yield (delta, done, finish_reason)."""
