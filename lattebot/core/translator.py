from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from discord.app_commands.translator import (
    Translator as _Translator,
    locale_str,
)

__all__ = ('Translator',)

if TYPE_CHECKING:
    from discord import Locale
    from discord.app_commands import TranslationContext

    from .bot import LatteBot


log = logging.getLogger('latte.translator')


class Translator(_Translator):
    def __init__(
        self,
        bot: LatteBot,
    ) -> None:
        super().__init__()
        self.bot = bot

    async def load(self) -> None:
        log.info('loaded')

    async def unload(self) -> None:
        log.info('unloaded')

    async def translate(
        self,
        string: locale_str,
        locale: Locale,
        context: TranslationContext,  # type: ignore[type-arg]
    ) -> str | None: ...
