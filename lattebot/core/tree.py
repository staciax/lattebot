from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from discord import app_commands
from discord.abc import Snowflake
from discord.http import Route

__all__ = ('LatteTree',)

if TYPE_CHECKING:
    from discord.abc import Snowflake
    from discord.app_commands import AppCommand

    from lattebot.core.bot import LatteBot

    from .translator import Translator


log = logging.getLogger('lattebot.tree')


class LatteTree(app_commands.CommandTree['LatteBot']):
    if TYPE_CHECKING:

        @property
        def translator(self) -> Translator | None: ...

        async def set_translator(self, translator: Translator | None) -> None:  # type: ignore[override]
            ...

    async def fake_translator(self, *, guild: Snowflake | None = None) -> None:
        if self.translator is None:
            return
        commands = self._get_all_commands(guild=guild)
        for command in commands:
            await command.get_translated_payload(self, self.translator)

    async def sync(self, *, guild: Snowflake | None = None) -> list[AppCommand]:
        try:
            sync_commands = await super().sync(guild=guild)
        finally:
            translator = self.translator
            if translator:
                translator.app_command_translator.reset_context()

        await self._attach_command_models(guild=guild)

        return sync_commands

    async def _attach_command_models(self, guild: Snowflake | None = None) -> None:
        app_commands_models = await self.fetch_commands(guild=guild, with_localizations=True)
        for app_command_model in app_commands_models:
            command = self.get_command(app_command_model.name, type=app_command_model.type)
            if command is None:
                log.warning('not found command: %s (type: %s)', app_command_model.name, app_command_model.type.name)
                continue
            command.extras['model'] = app_command_model

    # NOTE: wait for discord.py adding this feature
    # https://github.com/Rapptz/discord.py/pull/9452

    async def fetch_commands(
        self,
        *,
        guild: Snowflake | None = None,
        with_localizations: bool = False,
    ) -> list[app_commands.AppCommand]:
        if self.client.application_id is None:
            raise app_commands.errors.MissingApplicationID

        application_id = self.client.application_id

        if guild is None:
            commands = await self._http.request(
                Route('GET', '/applications/{application_id}/commands', application_id=application_id),
                params={'with_localizations': int(with_localizations)},
            )
        else:
            commands = await self._http.request(
                Route(
                    'GET',
                    '/applications/{application_id}/guilds/{guild_id}/commands',
                    application_id=application_id,
                    guild_id=guild.id,
                ),
                params={'with_localizations': int(with_localizations)},
            )

        return [app_commands.AppCommand(data=data, state=self._state) for data in commands]
