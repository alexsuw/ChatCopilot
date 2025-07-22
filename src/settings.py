from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr

class Settings(BaseSettings):
    bot_token: SecretStr
    
    # vLLM Configuration
    vllm_url: str = "http://localhost:8000"
    vllm_model_name: str = "Qwen/Qwen3-4B"
    vllm_max_tokens: int = 2048
    vllm_temperature: float = 0.7
    vllm_timeout: int = 30
    
    # Supabase
    supabase_url: str
    supabase_anon_key: SecretStr
    supabase_service_key: SecretStr

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings() 