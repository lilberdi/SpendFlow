from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    app_name: str = 'SpendFlow Backend'
    app_env: str = Field(default='dev', alias='APP_ENV')
    database_url: str = Field(default='postgresql+psycopg2://spendflow:spendflow@db:5432/spendflow', alias='DATABASE_URL')
    spendflow_total_limit: float = Field(default=100_000.0, alias='SPENDFLOW_TOTAL_LIMIT')
    cors_origins: str = Field(
        default='http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173',
        alias='CORS_ORIGINS',
    )


settings = Settings()
