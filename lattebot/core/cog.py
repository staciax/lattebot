from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Callable, Coroutine, Iterable, Self  # noqa: UP035

import discord
from discord import Interaction, Member, Message, User, app_commands
from discord.ext import commands
from discord.utils import MISSING

__all__ = (
    'LatteCog',
    'context_menu',
)

if TYPE_CHECKING:
    from discord.app_commands import ContextMenu, Group, locale_str

    from lattebot.core.bot import LatteBot

type Coro[T] = Coroutine[Any, Any, T]

if TYPE_CHECKING:
    type Binding = Group | commands.Cog
    type ContextMenuCallback[GroupT: Binding] = (
        Callable[[GroupT, 'Interaction[LatteBot]', Member], Coro[Any]]
        | Callable[[GroupT, 'Interaction[LatteBot]', User], Coro[Any]]
        | Callable[[GroupT, 'Interaction[LatteBot]', Message], Coro[Any]]
        | Callable[[GroupT, 'Interaction[LatteBot]', Member | User], Coro[Any]]
    )
else:
    type ContextMenuCallback[T] = Callable[..., Coro[T]]


log = logging.getLogger(__name__)


# https://github.com/InterStella0/stella_bot/blob/bf5f5632bcd88670df90be67b888c282c6e83d99/utils/cog.py#L28
def context_menu[T: Binding](
    *,
    name: str | locale_str = MISSING,
    nsfw: bool = False,
    guilds: list[discord.abc.Snowflake] = MISSING,
    auto_locale_strings: bool = True,
    extras: dict[Any, Any] = MISSING,
) -> Callable[[ContextMenuCallback[T]], ContextMenu]:
    def inner(func: Any) -> Any:
        nonlocal name
        func.__context_menu_guilds__ = guilds
        if name is MISSING:
            name = func.__name__
        func.__context_menu__ = {
            'name': name,
            'nsfw': nsfw,
            'auto_locale_strings': auto_locale_strings,
            'extras': extras,
        }
        return func

    return inner


class LatteCog(commands.Cog):
    __cog_context_menus__: list[app_commands.ContextMenu]

    def get_context_menus(self) -> list[app_commands.ContextMenu]:
        try:
            return self.__cog_context_menus__
        except AttributeError:
            return []

    async def cog_app_command_error(
        self,
        interaction: discord.Interaction[LatteBot],  # type: ignore[override]
        error: app_commands.AppCommandError,
    ) -> None:
        command = interaction.command
        if command:
            log.error(
                'exception in %s command on %s cog',
                command.name,
                self.qualified_name,
                exc_info=error,
            )
        else:
            log.error('exception on %s cog', self.qualified_name, exc_info=error)
        interaction.client.dispatch('app_command_error', interaction, error)

    async def _inject(
        self,
        bot: LatteBot,  # type: ignore[override]
        override: bool,
        guild: discord.abc.Snowflake | None,
        guilds: list[discord.abc.Snowflake],  # type: ignore[override]
    ) -> Self:
        await super()._inject(bot, override, guild, guilds)

        # context menus in cog
        for method_name in dir(self):
            method = getattr(self, method_name)
            if context_values := getattr(method, '__context_menu__', None):
                menu = app_commands.ContextMenu(callback=method, **context_values)
                menu.error(self.cog_app_command_error)
                menu.__binding__ = self  # type: ignore[attr-defined]
                context_values['context_menu_class'] = menu
                bot.tree.add_command(menu, guilds=method.__context_menu_guilds__)
                try:
                    self.__cog_context_menus__.append(menu)
                except AttributeError:
                    self.__cog_context_menus__ = [menu]

        return self

    async def _eject(self, bot: LatteBot, guild_ids: Iterable[int] | None) -> None:  # type: ignore[override]
        await super()._eject(bot, guild_ids)

        # context menus in cog
        for method_name in dir(self):
            method = getattr(self, method_name)
            if context_values := getattr(method, '__context_menu__', None):
                if menu := context_values.get('context_menu_class'):
                    bot.tree.remove_command(menu.name, type=menu.type)
                    try:
                        self.__cog_context_menus__.remove(menu)
                    except ValueError:
                        pass
