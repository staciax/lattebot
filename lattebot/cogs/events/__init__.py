from __future__ import annotations

from typing import TYPE_CHECKING

from .main import Event

if TYPE_CHECKING:
    from lattebot.core.bot import LatteBot


async def setup(bot: LatteBot) -> None:
    await bot.add_cog(Event(bot))
