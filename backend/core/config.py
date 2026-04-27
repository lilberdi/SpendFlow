from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    app_name: str = 'SpendFlow Backend'
    app_env: str = Field(default='dev', alias='APP_ENV')
    database_url: str = Field(default='postgresql+psycopg2://spendflow:spendflow@db:5432/spendflow', alias='DATABASE_URL')


settings = Settings()
