#Config of backend 
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    gemini_api_key : str
    tavily_api_key : str
    langchain_api_key: str = ""
    langchain_tracing_v2: str = "false"
    model_name : str = "gemini-2.5-flash"
    sqlite_db_path: str = "/data/checkpoints.db"

    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()

