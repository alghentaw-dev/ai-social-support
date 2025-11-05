
from typing import Optional
import grpc  # type: ignore
# If your llm_protos package is in Python path, import it; otherwise vendor as a submodule.
try:
    from llmruntime.v1 import llm_pb2, llm_pb2_grpc  # type: ignore
except Exception:
    llm_pb2 = None
    llm_pb2_grpc = None

class LLMClient:
    def __init__(self, addr: str, model: str | None = None):
        self.addr = addr
        self.model = model or ""

    def polish(self, text: str, instruction: str = "Rewrite concisely and clearly") -> str:
        if not llm_pb2 or not llm_pb2_grpc or not self.model:
            return text  # LLM disabled → return original
        channel = grpc.insecure_channel(self.addr)
        stub = llm_pb2_grpc.LLMRuntimeStub(channel)
        req = llm_pb2.GenerateRequest(
            model=self.model,
            messages=[llm_pb2.Message(role="system", content=instruction),
                      llm_pb2.Message(role="user", content=text)]
        )
        resp = stub.Generate(req, timeout=10)
        return resp.content or text
