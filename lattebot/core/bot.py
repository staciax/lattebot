import asyncio
import logging
from typing import Any

import aiohttp
import discord
from discord.ext import commands

from .config import settings
from .translator import Translator
from .tree import LatteTree

__all__ = ('LatteBot',)

log = logging.getLogger('latte')

description = "Hello, I'm latte bot, a bot made by stacia."

INITIAL_EXTENSIONS = (
    'lattebot.cogs.events',
    'lattebot.cogs.jsk',
    'lattebot.cogs.test',
)


class LatteBot(commands.AutoShardedBot):
    user: discord.ClientUser
    bot_app_info: discord.AppInfo
    tree: LatteTree  # type: ignore[assignment]

    def __init__(self) -> None:
        # intents
        intents = discord.Intents.none()
        intents.guilds = True
        intents.emojis_and_stickers = True
        # intents.dm_messages = True

        # allowed_mentions
        allowed_mentions = discord.AllowedMentions(
            roles=False,
            everyone=False,
            replied_user=False,
            users=True,
        )

        super().__init__(
            command_prefix=[],
            help_command=None,
            allowed_mentions=allowed_mentions,
            case_insensitive=True,
            intents=intents,
            description=description,
            enable_debug_events=True,
            application_id=settings.APPLICATION_ID,
            tree_cls=LatteTree,
            activity=discord.Activity(type=discord.ActivityType.listening, name='latte ♡ ₊˚'),
        )

    async def on_ready(self) -> None:
        log.info(
            f'logged in as: {self.user} '
            + (f'activity: {self.activity.name} ' if self.activity else '')
            + f'servers: {len(self.guilds)} '
            + f'users: {sum(guild.member_count for guild in self.guilds if guild.member_count)}'
        )

    @property
    def owner(self) -> discord.User:
        """Returns the bot owner."""
        return self.bot_app_info.owner

    @property
    def support_guild_id(self) -> int:
        return settings.SUPPORT_GUILD_ID
        # return self.bot_app_info.guild_id or settings.SUPPORT_GUILD_ID

    async def setup_hook(self) -> None:
        self.session = aiohttp.ClientSession()

        self.translator = Translator(self)
        await self.tree.set_translator(self.translator)

        self.bot_app_info = await self.application_info()
        self.owner_ids = [self.bot_app_info.owner.id]

        await self.cogs_load()
        # await self.tree_sync()

    async def tree_sync(self, guild_only: bool = False) -> None:
        # tree sync application commands
        if not guild_only:
            await self.tree.sync()

        # tree sync guild commands
        try:
            await self.tree.sync(guild=discord.Object(id=self.support_guild_id))
        except Exception as e:
            log.error(f'Failed to sync guild {self.support_guild_id}.', exc_info=e)

    async def cogs_load(self) -> None:
        await asyncio.gather(*[self.load_extension(extension) for extension in INITIAL_EXTENSIONS])

    async def cogs_unload(self) -> None:
        await asyncio.gather(*[self.unload_extension(extension) for extension in INITIAL_EXTENSIONS])

    async def on_message(self, message: discord.Message, /) -> None:
        if message.author == self.user:
            return

        await self.process_commands(message)

    async def on_error(self, event_method: str, /, *args: Any, **kwargs: Any) -> None:
        log.error('Ignoring exception in %s', event_method)

    async def load_extension(self, name: str, *, package: str | None = None) -> None:
        try:
            await super().load_extension(name, package=package)
        except Exception as e:
            log.error('failed to load extension %s', name, exc_info=e)
            raise e
        else:
            log.info('loaded extension %s', name)

    async def unload_extension(self, name: str, *, package: str | None = None) -> None:
        try:
            await super().unload_extension(name, package=package)
        except Exception as e:
            log.error('failed to unload extension %s', name, exc_info=e)
            raise e
        else:
            log.info('unloaded extension %s', name)

    async def reload_extension(self, name: str, *, package: str | None = None) -> None:
        try:
            await super().reload_extension(name, package=package)
        except Exception as e:
            log.error('failed to reload extension %s', name, exc_info=e)
            raise e
        else:
            log.info('reloaded extension %s', name)

    async def start(self) -> None:  # type: ignore[override]
        await super().start(token=settings.DISCORD_TOKEN, reconnect=True)

    async def close(self) -> None:
        log.info('Bot is shutting down...')

        await self.cogs_unload()
        await self.session.close()

        await super().close()
