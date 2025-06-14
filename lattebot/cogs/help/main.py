from __future__ import annotations

from typing import TYPE_CHECKING, Any, Self

import discord
from discord import app_commands, ui
from discord.app_commands import locale_str as _
from discord.app_commands.checks import bot_has_permissions, dynamic_cooldown
from discord.app_commands.commands import Command, ContextMenu, Group
from discord.app_commands.models import AppCommand

from lattebot.checks import cooldown_short
from lattebot.core.cog import LatteCog
from lattebot.embeds import Embed
from lattebot.ui.view import ViewAuthor

from .paginator import LattePages, ListPageSource

if TYPE_CHECKING:
    from discord.ext import commands

    from lattebot.core.bot import LatteBot

# TODO: add translations


def help_command_embed(interaction: discord.Interaction[LatteBot]) -> Embed:
    embed = Embed(timestamp=interaction.created_at)
    embed.set_author(
        name=f'{interaction.client.user.display_name} - ' + '_(help.command)',
        icon_url=interaction.client.user.display_avatar,
    )
    embed.set_image(
        url='https://cdn.discordapp.com/attachments/1001848697316987009/1001848873385472070/help_banner.png'
    )
    return embed


def cog_embed(cog: commands.Cog | LatteCog, _locale: discord.Locale) -> Embed:
    emoji = getattr(cog, 'display_emoji', '')

    # translator = cog.bot.translator
    # description = translator.translate_text(_('cog.description'), locale=locale)

    return Embed(
        title=f'{emoji} {cog.qualified_name}',
        description=cog.description + '\n',
    )


class HelpPageSource(ListPageSource[Command[Any, ..., Any] | Group]):
    def __init__(self, cog: commands.Cog | LatteCog, source: list[Command[Any, ..., Any] | Group]) -> None:
        super().__init__(sorted(source, key=lambda c: c.qualified_name), per_page=6)
        self.cog = cog

    def format_page(  # type: ignore[override]
        self,
        menu: HelpCommandView,
        entries: list[Command[Any, ..., Any] | Group],
    ) -> Embed:
        embed = cog_embed(self.cog, menu.locale)

        if embed.description is None:
            embed.description = ''

        for command in entries:
            name = command.qualified_name
            description = command.description
            model: AppCommand | None = command.extras.get('model')
            if isinstance(model, AppCommand):
                name = model.mention
                description = model.description_localizations.get(menu.locale, description)
            embed.description += f'\n{name} - {description}'

        return embed


class CogButton(ui.Button['HelpCommandView']):
    def __init__(
        self,
        cog: commands.Cog | LatteCog,
        entries: list[Command[Any, ..., Any] | Group],
        **kwargs: Any,
    ) -> None:
        super().__init__(emoji=getattr(cog, 'display_emoji'), style=discord.ButtonStyle.primary, **kwargs)  # noqa: B009
        self.cog = cog
        self.entries = entries
        if self.emoji is None:
            self.label = cog.qualified_name

    async def callback(self, interaction: discord.Interaction[LatteBot]) -> None:  # type: ignore[override]
        assert self.view is not None  # noqa: S101
        self.view.source = HelpPageSource(self.cog, self.entries)

        max_pages = self.view.source.get_max_pages()
        if max_pages > 1:
            self.view.add_nav_buttons()
        else:
            self.view.remove_nav_buttons()

        self.disabled = True
        for child in self.view.children:
            if isinstance(child, CogButton) and child != self:
                child.disabled = False

        self.view.home_button.disabled = False
        await self.view.show_page(interaction, 0)


class HelpCommandView(ViewAuthor, LattePages):
    def __init__(self, interaction: discord.Interaction[LatteBot], allowed_cogs: tuple[str, ...]) -> None:
        super().__init__(interaction=interaction, timeout=60.0 * 30)  # 30 minutes
        self.allowed_cogs = allowed_cogs
        self.embed: Embed = help_command_embed(interaction)
        # fmt: off
        self.go_to_last_page.row = self.go_to_first_page.row = self.go_to_previous_page.row = self.go_to_next_page.row = 1
        # fmt: on
        self.clear_items()
        self.add_item(self.home_button)
        # self.cooldown = commands.CooldownMapping.from_cooldown(8.0, 15.0, user_check)  # TODO: overide default cooldown

    def _update_labels(self, page_number: int) -> None:
        super()._update_labels(page_number)
        self.go_to_next_page.label = 'next'
        self.go_to_previous_page.label = 'prev'

    def add_nav_buttons(self) -> None:
        self.add_item(self.home_button)
        self.add_item(self.go_to_previous_page)
        self.add_item(self.go_to_next_page)
        self.add_item(self.go_to_last_page)

    def remove_nav_buttons(self) -> None:
        self.remove_item(self.go_to_first_page)
        self.remove_item(self.go_to_previous_page)
        self.remove_item(self.go_to_next_page)
        self.remove_item(self.go_to_last_page)

    async def build_cog_buttons(self) -> None:
        user = self.interaction.user
        channel = self.interaction.channel

        async def command_available(command: Command[Any, ..., Any] | Group | ContextMenu) -> bool:
            # it fine my bot is not nsfw
            # if (
            #     command.nsfw
            #     and channel is not None
            #     and not isinstance(channel, (discord.GroupChannel, discord.DMChannel))
            #     and not channel.is_nsfw()
            # ):
            #     return False

            if await self.bot.is_owner(user):
                return True

            if isinstance(command, Group):
                return False

            if command._guild_ids:
                return False

            # ignore slash commands that are not global
            if not isinstance(command, ContextMenu) and command.parent and command.parent._guild_ids:
                return False

            # ignore slash commands you can't run
            if command.checks and not await discord.utils.async_all(f(self.interaction) for f in command.checks):
                return False

            # ignore slash commands you not have default permissions
            return not (
                command.default_permissions
                and channel is not None
                and isinstance(user, discord.Member)
                and not channel.permissions_for(user) >= command.default_permissions
            )

        for cog in sorted(self.bot.cogs.values(), key=lambda c: c.qualified_name.lower()):
            if cog.qualified_name.lower() not in self.allowed_cogs:
                continue

            if not list(cog.walk_app_commands()):
                continue

            entries = []
            for command in cog.walk_app_commands():
                if not await command_available(command):
                    continue
                entries.append(command)

            # TODO: implement context menu
            # if isinstance(cog, Cog):
            #     context_menus = cog.get_context_menus()
            #     for menu in context_menus:
            #         if not await command_available(menu):
            #             continue
            #         entries.append(menu)

            if not entries:
                continue

            self.add_item(CogButton(cog, entries))

    async def before_callback(self, interaction: discord.Interaction[LatteBot]) -> None:
        if self.locale == interaction.locale:
            return
        self.locale = interaction.locale
        self.embed = help_command_embed(interaction)

    async def start(self) -> None:  # type: ignore[override]
        await self.build_cog_buttons()
        await self.interaction.response.send_message(embed=self.embed, view=self)
        self.message = await self.interaction.original_response()

    @ui.button(emoji='🏘️', style=discord.ButtonStyle.primary, disabled=True)
    async def home_button(self, interaction: discord.Interaction[LatteBot], button: ui.Button[Self]) -> None:
        # disable home button
        button.disabled = True

        # disable all cog buttons
        for child in self.children:
            if isinstance(child, CogButton):
                child.disabled = False

        # remove nav buttons
        self.remove_nav_buttons()

        await interaction.response.edit_message(embed=self.embed, view=self)


class Help(LatteCog, name='help'):
    """Help command."""

    @app_commands.command(name=_('help'), description=_('help command'))
    # @app_commands.default_permissions(send_messages=True, embed_links=True)
    @bot_has_permissions(send_messages=True, embed_links=True)
    @dynamic_cooldown(cooldown_short)
    async def help_command(self, interaction: discord.Interaction[LatteBot]) -> None:
        cogs = ('about', 'valorant')
        help_command = HelpCommandView(interaction, cogs)
        await help_command.start()
