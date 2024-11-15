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
    @app_commands.describe(
        param_str=_('string parameter'),
        param_int=_('integer parameter'),
        param_float=_('float parameter'),
    )
    @app_commands.choices(
        param_str=[
            app_commands.Choice(name='str 1', value='str_1'),
            app_commands.Choice(name='str 2', value='str_2'),
            app_commands.Choice(name='str 3', value='str_3'),
        ],
        param_int=[
            app_commands.Choice(name='int 1', value=1),
            app_commands.Choice(name='int 2', value=2),
            app_commands.Choice(name='int 3', value=3),
        ],
        param_float=[
            app_commands.Choice(name='float 1', value=1.5),
            app_commands.Choice(name='float 2', value=2.5),
            app_commands.Choice(name='float 3', value=3.5),
        ],
    )  # type: ignore[misc]
    async def test_command(
        self,
        interaction: discord.Interaction[LatteBot],
        param_str: app_commands.Choice[str],
        param_int: app_commands.Choice[int],
        param_float: app_commands.Choice[float],
    ) -> None:
        content = f'param_str: {param_str.value}, param_int: {param_int.value}, param_float: {param_float.value}'
        await interaction.response.send_message(content, ephemeral=True)


async def setup(bot: LatteBot) -> None:
    await bot.add_cog(Test(bot), guild=discord.Object(bot.support_guild_id))
