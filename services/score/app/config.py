# services/score/app/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "Eligibility Scoring Service"
    MODEL_DIR: str = "/app/models/eligibility_v1"
    PORT: int = 8004

    class Config:
        env_prefix = "SCORE_"

settings = Settings()
