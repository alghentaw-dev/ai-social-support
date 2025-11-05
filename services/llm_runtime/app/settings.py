from pydantic_settings import BaseSettings, SettingsConfigDict
import os

class Settings(BaseSettings):
    # Server
    LLMR_LISTEN_HOST: str = "0.0.0.0"
    LLMR_PORT: int = 51051

    # Defaults
    DEFAULT_PROVIDER: str = "openai"          # "openai" | "ollama"
    DEFAULT_MODEL: str = "gpt-4o-mini"        # OpenAI default

    # OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"

    # Ollama
    OLLAMA_ENDPOINT: str = "http://ollama:11434"

    # Langfuse (Cloud)
    LANGFUSE_PUBLIC_KEY: str | None = os.getenv("LANGFUSE_PUBLIC_KEY")
    LANGFUSE_SECRET_KEY: str | None = os.getenv("LANGFUSE_SECRET_KEY")
    LANGFUSE_HOST: str = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

    # Optional: allow .env and ignore unknown envs
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
