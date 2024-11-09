from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord

from lattebot.core.cog import LatteCog
from lattebot.core.config import settings

if TYPE_CHECKING:
    from lattebot.core.bot import LatteBot

log = logging.getLogger(__name__)


class Event(LatteCog, name='events'):
    """Bot Events."""

    @discord.utils.cached_property
    def webhook(self) -> discord.Webhook:
        wh_id, wh_token = settings.GUILD_WEBHOOK_ID, settings.GUILD_WEBHOOK_TOKEN
        hook = discord.Webhook.partial(wh_id, wh_token, session=self.bot.session)
        return hook  # noqa: RET504

    async def send_guild_stats(self, embed: discord.Embed, guild: discord.Guild) -> None:
        """Send guild stats to webhook."""
        member_count = guild.member_count or 1

        embed.description = (
            f'**ɴᴀᴍᴇ:** {discord.utils.escape_markdown(guild.name)} • `{guild.id}`\n**ᴏᴡɴᴇʀ:** `{guild.owner_id}`'
        )
        embed.add_field(name='ᴍᴇᴍʙᴇʀ ᴄᴏᴜɴᴛ', value=f'{member_count}', inline=True)
        embed.set_thumbnail(url=guild.icon)
        embed.set_footer(text=f'ᴛᴏᴛᴀʟ ɢᴜɪʟᴅꜱ: {len(self.bot.guilds)}')

        if guild.me:
            embed.timestamp = guild.me.joined_at

        await self.webhook.send(embed=embed, silent=True)

    @LatteCog.listener('on_guild_join')
    async def on_latte_join(self, guild: discord.Guild) -> None:
        """Call when LatteBot joins a guild."""
        # TODO: Blacklist check

        embed = discord.Embed(title='ᴊᴏɪɴᴇᴅ ꜱᴇʀᴠᴇʀ')
        await self.send_guild_stats(embed, guild)

    @LatteCog.listener('on_guild_remove')
    async def on_latte_leave(self, guild: discord.Guild) -> None:
        """Call when LatteBot leaves a guild."""
        embed = discord.Embed(title='ʟᴇꜰᴛ ꜱᴇʀᴠᴇʀ')
        await self.send_guild_stats(embed, guild)


async def setup(bot: LatteBot) -> None:
    await bot.add_cog(Event(bot))
