from pydantic_settings import BaseSettings, SettingsConfigDict

__all__ = ('settings',)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env',
        env_ignore_empty=True,
        extra='ignore',
    )

    PROJECT_NAME: str
    APPLICATION_ID: int
    SUPPORT_GUILD_ID: int
    DISCORD_TOKEN: str


settings = Settings()  # type: ignore[call-arg]
