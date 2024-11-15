from __future__ import annotations

from typing import TYPE_CHECKING

from .main import About

if TYPE_CHECKING:
    from lattebot.core.bot import LatteBot


async def setup(bot: LatteBot) -> None:
    await bot.add_cog(About(bot))
