from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr

class Settings(BaseSettings):
    bot_token: SecretStr
    
    # AI Services
    openai_api_key: SecretStr
    pinecone_api_key: SecretStr
    pinecone_host: str
    google_api_key: SecretStr
    
    # Supabase
    supabase_url: str
    supabase_anon_key: SecretStr
    supabase_service_key: SecretStr

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings() 