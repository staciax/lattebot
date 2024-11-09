from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.app_commands import locale_str as _

from lattebot.core.cog import LatteCog, context_menu

if TYPE_CHECKING:
    from lattebot.core.bot import LatteBot


class Test(LatteCog, name='test'):
    def __init__(self, bot: LatteBot) -> None:
        self.bot: LatteBot = bot

    @context_menu(name=_('context_message'))
    async def test_context_message(self, interaction: discord.Interaction[LatteBot], message: discord.Message) -> None:
        await interaction.response.send_message(f'content: {message.content}', ephemeral=True)

    @context_menu(name=_('context_user'))
    async def test_context_user(self, interaction: discord.Interaction[LatteBot], user: discord.User) -> None:
        await interaction.response.send_message(f'username: {user.name}', ephemeral=True)

    @app_commands.command(name=_('command'), description=_('command description'))
    async def test_command(self, interaction: discord.Interaction[LatteBot]) -> None:
        await interaction.response.send_message('command response', ephemeral=True)


async def setup(bot: LatteBot) -> None:
    await bot.add_cog(Test(bot), guild=discord.Object(bot.support_guild_id))
