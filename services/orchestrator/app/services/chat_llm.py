# services/orchestrator/app/services/chat_llm.py
import os
from typing import Optional, Dict, Any

import grpc
from llmruntime.v1 import llm_pb2, llm_pb2_grpc  # from packages/llm_protos
from app.observability.langfuse import generation, end_safe
LLM_ADDR = os.getenv("LLM_RUNTIME_ADDR", "llm_runtime:51051")


def generate_answer(
    *,
    prompt: str,
    system: str = "",
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    options: Optional[Dict[str, Any]] = None,
    timeout: float = 60.0,
) -> str:
    """
    Simple wrapper over LLM Runtime Generate.
    Returns plain text (no JSON parsing).
    """
    channel = grpc.insecure_channel(LLM_ADDR)
    stub = llm_pb2_grpc.LlmRuntimeStub(channel)

    req = llm_pb2.GenerateRequest(
        model=(model or ""),
        prompt=prompt,
        system=(system or ""),
        json_mode=False,
        json_schema="",
        options=(options or {}),
    )

    if temperature is not None:
        req.temperature = float(temperature)
    if max_tokens is not None:
        req.max_tokens = int(max_tokens)

   
    # 📈 Langfuse generation
    gen = generation(
        name="chat.generate_answer",
        model=(model or "llm-runtime-default"),
        prompt=prompt,
        system=system,
        metadata={"component": "orchestrator.chat_llm"},
    )
    try:
        resp = stub.Generate(req, timeout=timeout)
        text = resp.text or ""
        gen.update(output=text)
        return text
    finally:
        end_safe(gen)
