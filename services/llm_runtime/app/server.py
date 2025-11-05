from concurrent import futures
import grpc
from app.settings import settings
from app.service_impl import LlmRuntimeService
from llmruntime.v1 import llm_pb2_grpc  # <-- top-level package import

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=16))
    llm_pb2_grpc.add_LlmRuntimeServicer_to_server(LlmRuntimeService(), server)
    listen = f"{settings.LLMR_LISTEN_HOST}:{settings.LLMR_PORT}"
    server.add_insecure_port(listen)
    print(f"[llm-runtime] listening on {listen} (default: {settings.DEFAULT_PROVIDER}/{settings.DEFAULT_MODEL})")
    server.start()
    server.wait_for_termination()

if __name__ == "__main__":
    serve()
