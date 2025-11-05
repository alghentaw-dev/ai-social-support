from crewai import BaseLLM
from typing import Any, Dict, List, Optional, Union
from app.services.chat_llm import generate_answer


class LocalLLMAdapter(BaseLLM):
    """
    Minimal CrewAI-compatible LLM adapter that wraps our chat_llm.generate_answer().
    It satisfies CrewAI's BaseLLM interface but doesn't talk to any external provider.
    """

    def __init__(self, model: Optional[str] = None, temperature: float = 0.2):
        super().__init__(model=model or "local-llm", temperature=temperature)

    def call(
        self,
        messages: Union[str, List[Dict[str, str]]],
        tools: Optional[List[dict]] = None,
        callbacks: Optional[List[Any]] = None,
        available_functions: Optional[Dict[str, Any]] = None,
        **kwargs: Any,  # 👈 catch anything unexpected like from_task
    ) -> str:
        """Flatten chat-style messages to a single prompt and call generate_answer()."""
        if isinstance(messages, str):
            system_text = ""
            user_text = messages
        else:
            system_text = "\n".join(
                m["content"] for m in messages if m.get("role") == "system"
            )
            user_text = "\n".join(
                m["content"] for m in messages if m.get("role") != "system"
            )

        return generate_answer(prompt=user_text, system=system_text)

    def supports_function_calling(self) -> bool:
        return False

    def get_context_window_size(self) -> int:
        return 8192
