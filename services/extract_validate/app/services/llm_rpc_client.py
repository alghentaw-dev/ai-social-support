# services/extract_validate/app/services/llm_rpc_client.py
import os
import json
import grpc
from typing import Optional, Dict, Any

from llmruntime.v1 import llm_pb2, llm_pb2_grpc  # stubs from packages/llm_protos

LLM_ADDR = os.getenv("LLM_RUNTIME_ADDR", "llm_runtime:51051")

def _best_effort_json(text: str) -> Dict[str, Any]:
    s = text.strip()
    if s.startswith("```"):
        s = s.strip("` \n")
        if s.lower().startswith("json"):
            s = s[4:].lstrip()
    try:
        return json.loads(s)
    except Exception:
        return {}

def ask_json(
    *,
    prompt: str,
    model: Optional[str] = None,
    system: Optional[str] = None,
    options: Optional[Dict[str, str]] = None,
    json_schema: Optional[Dict[str, Any] | str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    request_id: Optional[str] = None,
    user_id: Optional[str] = None,
    timeout: float = 60.0,
) -> Dict[str, Any]:
    """
    Pure transport: forwards all fields to LLM Runtime and parses JSON.
    No embedded prompts or templates here.
    """
    schema_str = ""
    if isinstance(json_schema, dict):
        schema_str = json.dumps(json_schema)
    elif isinstance(json_schema, str):
        schema_str = json_schema

    channel = grpc.insecure_channel(LLM_ADDR)
    stub = llm_pb2_grpc.LlmRuntimeStub(channel)

    req = llm_pb2.GenerateRequest(
        model=(model or ""),
        prompt=prompt,
        system=(system or ""),
        json_mode=bool(schema_str),   # enable JSON mode if a schema is provided
        json_schema=schema_str,
        options=(options or {}),
    )
    if temperature is not None:
        req.temperature = float(temperature)
    if max_tokens is not None:
        req.max_tokens = int(max_tokens)
    if request_id:
        req.request_id = request_id
    if user_id:
        req.user_id = user_id

    resp = stub.Generate(req, timeout=timeout)
    return _best_effort_json(resp.text)
