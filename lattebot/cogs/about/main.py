from __future__ import annotations

import datetime
import itertools
import platform
import tomllib
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING, Any

import discord
import pygit2
from discord import app_commands
from discord.app_commands import locale_str as _
from discord.app_commands.checks import bot_has_permissions
from discord.utils import format_dt

from lattebot.core.bot import LatteBot
from lattebot.core.cog import LatteCog
from lattebot.embeds import LocalizedEmbed
from lattebot.ui.view import View

# import pkg_resources

if TYPE_CHECKING:
    from lattebot.core.bot import LatteBot


def get_latest_commits(limit: int = 3) -> str:
    """Get the latest commits from the repo."""
    repo = pygit2.Repository('./.git')
    commits = list(itertools.islice(repo.walk(repo.head.target, pygit2.enums.SortMode.TOPOLOGICAL), limit))
    return '\n'.join(format_commit(c) for c in commits)


def format_commit(commit: pygit2.Commit) -> str:
    """Format a commit."""
    short, _, _ = commit.message.partition('\n')
    short = short[0:40] + '...' if len(short) > 40 else short  # noqa: PLR2004
    short_sha2 = commit.short_id[0:6]
    commit_tz = datetime.timezone(datetime.timedelta(minutes=commit.commit_time_offset))
    commit_time = datetime.datetime.fromtimestamp(commit.commit_time).astimezone(commit_tz)
    offset = format_dt(commit_time, style='R')
    return f'[`{short_sha2}`](https://github.com/staciax/lattebot/commit/{commit.short_id}) {short} ({offset})'


@cache
def get_version() -> Any:
    with Path('pyproject.toml').open('rb') as fp:
        pyproject = tomllib.load(fp)
        version = pyproject['project']['version']
        return version  # noqa: RET504


class About(LatteCog, name='about'):
    """Commands to show information about the bot."""

    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return discord.PartialEmoji(name='latte', id=998453861511610398)

    @app_commands.command(name=_('about'), description=_('Shows bot information'))
    @bot_has_permissions(send_messages=True, embed_links=True)
    async def about(self, interaction: discord.Interaction[LatteBot]) -> None:
        translator = self.bot.translator
        locale = interaction.locale

        guild_count = len(self.bot.guilds)
        member_count = sum(guild.member_count for guild in self.bot.guilds if guild.member_count is not None)
        total_commands = len(self.bot.tree.get_commands())
        # dpy_version = pkg_resources.get_distribution('discord.py').version

        version = get_version()
        python_version = platform.python_version()
        latest_commits = get_latest_commits(limit=5)

        embed = LocalizedEmbed(
            translator=translator,
            locale=locale,
            timestamp=interaction.created_at,
            color=0xC0AEE0,
        )

        embed.set_author(
            name=_('about.bot'),
            icon_url=self.bot.user.avatar if self.bot.user else None,
        )

        embed.add_field(
            name=_('about.bot_latest_update'),
            value=latest_commits,
            inline=False,
        )

        # TODO: constants for emojis

        embed.add_field(
            name=_('about.bot_stats'),
            value='\n'.join([
                f'{self.bot.get_application_emoji("lattebot")} ꜱᴇʀᴠᴇʀꜱ: `{guild_count}`',
                f'{self.bot.get_application_emoji("member")} ᴜꜱᴇʀꜱ: `{member_count}`',
                f'{self.bot.get_application_emoji("slash")} ᴄᴏᴍᴍᴀɴᴅꜱ: `{total_commands}`',
            ]),
            inline=True,
        )
        embed.add_field(
            name=_('about.bot_info'),
            value='\n'.join([
                f'{self.bot.get_application_emoji("lattebot")} ʟᴀᴛᴛᴇ: `{version}`',
                f'{self.bot.get_application_emoji("python")} ᴘʏᴛʜᴏɴ: `{python_version}`',
                f'{self.bot.get_application_emoji("discord_py")} ᴅɪꜱᴄᴏʀᴅ.ᴘʏ: `{discord.__version__}`',
            ]),
        )

        embed.set_footer(
            text=_('about.developed_by', developer=self.bot.owner),
            icon_url=self.bot.owner.avatar,
        )

        # TODO: view support translation

        view = View()
        view.add_url_button(
            translator.translate_text(_('about.support_server'), locale),
            'https://discord.gg',
            emoji=self.bot.get_application_emoji('lattebot'),
        )
        view.add_url_button(
            translator.translate_text(_('about.developer'), locale),
            'https://github.com/staciax',
            emoji=self.bot.get_application_emoji('stacia_dev'),
        )

        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name=_('support'), description=_('Sends the support server of the bot.'))
    @bot_has_permissions(send_messages=True, embed_links=True)
    async def support(self, interaction: discord.Interaction[LatteBot]) -> None:
        translator = self.bot.translator
        locale = interaction.locale

        embed = LocalizedEmbed(translator=translator, locale=locale)
        embed.set_author(name='ꜱᴜᴘᴘᴏʀᴛ:', icon_url=self.bot.user.avatar)  # url=self.bot.support_invite_url
        embed.set_thumbnail(url=self.bot.user.avatar)

        view = View()
        view.add_url_button(
            translator.translate_text(_('about.support_server'), locale),
            'https://discord.gg',
            emoji=self.bot.get_application_emoji('lattebot'),
        )
        view.add_url_button(
            translator.translate_text(_('about.developer'), locale),
            'https://github.com/staciax',
            emoji=self.bot.get_application_emoji('stacia_dev'),
        )

        await interaction.response.send_message(embed=embed, view=view)
