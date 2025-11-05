from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PORT: int = 8002
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_SECURE: bool = False
    MINIO_BUCKET: str = "documents"


    LLM_ENDPOINT: str = "http://ollama:11434"  # docker service name
    LLM_MODEL: str = "llama3.2:latest"   # pulled above
settings = Settings()
