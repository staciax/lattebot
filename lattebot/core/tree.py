from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from discord import app_commands
from discord.abc import Snowflake

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
        return sync_commands
