
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "Recommendation Service"
    HOST: str = "0.0.0.0"
    PORT: int = 8006
    TAXONOMY_PATH: str = "/app/data/taxonomy.json"
    # optional LLM runtime grpc
    LLM_RUNTIME_ADDR: str = "llm_runtime:51051"
    LLM_MODEL: str = ""  # leave empty to skip LLM polish
    LOG_LEVEL: str = "info"

    class Config:
        env_prefix = "RECO_"

settings = Settings()
