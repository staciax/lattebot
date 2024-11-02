from pydantic_settings import BaseSettings, SettingsConfigDict

__all__ = ('settings',)


class EnvConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env',
        env_ignore_empty=True,
        extra='ignore',
    )


class Settings(EnvConfig):
    PROJECT_NAME: str
    APPLICATION_ID: int
    SUPPORT_GUILD_ID: int
    DISCORD_TOKEN: str

    # Webhook
    GUILD_WEBHOOK_ID: int
    GUILD_WEBHOOK_TOKEN: str


settings = Settings()  # type: ignore[call-arg]
