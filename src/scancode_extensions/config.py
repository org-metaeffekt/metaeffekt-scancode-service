from pydantic_settings import BaseSettings, SettingsConfigDict


class ServiceSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="scancode_service_")
    processes: int = 6


settings = ServiceSettings()
