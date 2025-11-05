import grpc
from app.settings import settings
from app.providers.openai_provider import OpenAIProvider
from app.providers.ollama_provider import OllamaProvider
from app.providers.base import BaseProvider
from app.observability.langfuse import start_trace, generation, end_safe
from llmruntime.v1 import llm_pb2, llm_pb2_grpc   # <-- top-level package import

def _choose_provider(model: str | None, explicit_provider: str | None) -> tuple[str, BaseProvider, str]:
    # Provider by model prefix or explicit default
    provider_name = explicit_provider or settings.DEFAULT_PROVIDER
    m = model or settings.DEFAULT_MODEL
    if m.startswith("ollama:"):
        provider_name = "ollama"
        m = m[len("ollama:"):]
    if provider_name == "ollama":
        return provider_name, OllamaProvider(), m
    return "openai", OpenAIProvider(), m

class LlmRuntimeService(llm_pb2_grpc.LlmRuntimeServicer):
    def Generate(self, request: llm_pb2.GenerateRequest, context: grpc.ServicerContext):
        provider_name, provider, model = _choose_provider(request.model, None)
        trace = start_trace(
            name="llm_runtime.generate",
            user_id=(request.user_id or None),
            metadata={"request_id": request.request_id or "", "model": request.model or "", "provider": self.provider.name},
        )
        text, finish = provider.generate(
            model=model,
            prompt=request.prompt,
            system=request.system or None,
            options=dict(request.options),
            json_mode=request.json_mode,
            json_schema=request.json_schema or None,
            max_tokens=(request.max_tokens or None),
            temperature=(request.temperature if request.temperature != 0 else None),
            timeout_ms=(request.timeout_ms or None)
        )
        end_safe(finish)
        end_safe(trace)
        return llm_pb2.GenerateResponse(
            text=text, model=model, provider=provider_name,
            finish_reason=finish or "stop", request_id=request.request_id or ""
        )

    def GenerateStream(self, request, context):
        provider_name, provider, model = _choose_provider(request.model, None)
        for delta, done, finish in provider.generate_stream(
            model=model,
            prompt=request.prompt,
            system=request.system or None,
            options=dict(request.options),
            json_mode=request.json_mode,
            json_schema=request.json_schema or None,
            max_tokens=(request.max_tokens or None),
            temperature=(request.temperature if request.temperature != 0 else None),
            timeout_ms=(request.timeout_ms or None)
        ):
            yield llm_pb2.GenerateChunk(
                delta=delta, model=model, provider=provider_name, done=done, finish_reason=finish or ""
            )

    def Health(self, request, context):
        return llm_pb2.HealthResponse(status="ok", provider_default=settings.DEFAULT_PROVIDER, model_default=settings.DEFAULT_MODEL)
