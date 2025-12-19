from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, Final

import discord
from discord import app_commands
from discord.app_commands import locale_str as _
from discord.app_commands.checks import bot_has_permissions

from lattebot.checks import owner_only
from lattebot.core.bot import INITIAL_EXTENSIONS
from lattebot.core.cog import LatteCog

if TYPE_CHECKING:
    from lattebot.core.bot import LatteBot


class Admin(LatteCog, name='admin'):
    """Admin commands."""

    extension = app_commands.Group(
        name=_('ext'),
        description=_('Extension management commands.'),
        default_permissions=discord.Permissions(
            administrator=True,
        ),
        guild_only=True,
        # allowed_contexts=,
        # allowed_installs=
    )

    INITIAL_EXTENSION_CHOICES: ClassVar[Final[list[app_commands.Choice[str]]]] = [
        app_commands.Choice(name=ext, value=ext) for ext in INITIAL_EXTENSIONS
    ]

    @extension.command(name=_('load'), description=_('Load an extension.'))
    @app_commands.choices(extension=INITIAL_EXTENSION_CHOICES)
    @app_commands.describe(extension=_('extension name'))
    @app_commands.rename(extension=_('extension'))
    @bot_has_permissions(send_messages=True, embed_links=True)
    @owner_only()
    async def extension_load(
        self, interaction: discord.Interaction[LatteBot], extension: app_commands.Choice[str]
    ) -> None:
        await interaction.response.defer(ephemeral=True)
        await self.bot.load_extension(extension.value)

        await interaction.followup.send(f'**Loaded**: `{extension.value}`', silent=True)

    @extension.command(name=_('unload'), description=_('Unload an extension.'))
    @app_commands.choices(extension=INITIAL_EXTENSION_CHOICES)
    @app_commands.describe(extension=_('extension name'))
    @app_commands.rename(extension=_('extension'))
    @bot_has_permissions(send_messages=True, embed_links=True)
    @owner_only()
    async def extension_unload(
        self, interaction: discord.Interaction[LatteBot], extension: app_commands.Choice[str]
    ) -> None:
        await interaction.response.defer(ephemeral=True)
        await self.bot.unload_extension(extension.value)

        await interaction.followup.send(f'**Unloaded**: `{extension.value}`', silent=True)

    @extension.command(name=_('reload'), description=_('Reload an extension.'))
    @app_commands.choices(extension=INITIAL_EXTENSION_CHOICES)
    @app_commands.describe(extension=_('extension name'))
    @app_commands.rename(extension=_('extension'))
    @bot_has_permissions(send_messages=True, embed_links=True)
    @owner_only()
    async def extension_reload(
        self, interaction: discord.Interaction[LatteBot], extension: app_commands.Choice[str]
    ) -> None:
        await interaction.response.defer(ephemeral=True)

        await self.bot.reload_extension(extension.value)

        await interaction.followup.send(f'**Reloaded**: `{extension.value}`', silent=True)

    @app_commands.command(name='sync', description='Syncs the application commands to Discord.')
    @app_commands.rename(guild_id=_('guild_id'))
    @app_commands.describe(guild_id=_('target guild id'))
    @bot_has_permissions(send_messages=True, embed_links=True)
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    @owner_only()
    async def sync_tree(self, interaction: discord.Interaction[LatteBot], guild_id: str | None = None) -> None:
        await interaction.response.defer(ephemeral=True)

        if guild_id and guild_id.isdigit():
            guild_obj = discord.Object(id=int(guild_id))
            commands_synced = await self.bot.tree.sync(guild=guild_obj)
        else:
            commands_synced = await self.bot.tree.sync()

        await interaction.followup.send(f'Synced {len(commands_synced)} commands.', ephemeral=True, silent=True)

    # @extension_load.autocomplete('extension')
    # @extension_unload.autocomplete('extension')
    # @extension_reload.autocomplete('extension')
    # async def extenion_autocomplete(self, interaction: Interaction, _current: str) -> list[app_commands.Choice[str]]:
    #     """Autocomplete for extension names."""
    #     if interaction.user.id != self.bot.owner_id:
    #         return [
    #             app_commands.Choice(name='Only owner can use this command', value='Owner only can use this command')
    #         ]

    #     cogs = [extension.lower() for extension in self.bot._initial_extensions if extension.lower() != 'cogs.admin']
    #     return [app_commands.Choice(name=cog, value=cog) for cog in cogs]
