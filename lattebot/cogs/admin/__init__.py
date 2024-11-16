from __future__ import annotations

from typing import TYPE_CHECKING

import discord

from .main import Admin

if TYPE_CHECKING:
    from lattebot.core.bot import LatteBot


async def setup(bot: LatteBot) -> None:
    await bot.add_cog(Admin(bot), guilds=[discord.Object(id=bot.support_guild_id)])
