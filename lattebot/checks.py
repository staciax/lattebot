from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.app_commands.checks import Cooldown

__all__ = (
    'cooldown_long',
    'cooldown_medium',
    'cooldown_short',
    'custom_cooldown',
    'owner_only',
)


if TYPE_CHECKING:
    from collections.abc import Callable

    from lattebot.core.bot import LatteBot


def user(interaction: discord.Interaction[LatteBot]) -> discord.User | discord.Member:
    return interaction.user


def owner_only[T]() -> Callable[[T], T]:
    async def actual_check(interaction: discord.Interaction[LatteBot]) -> bool:
        return await interaction.client.is_owner(interaction.user)

    return app_commands.check(actual_check)


def cooldown_short(interaction: discord.Interaction[LatteBot]) -> Cooldown | None:
    if interaction.user == interaction.client.owner:
        return None
    return Cooldown(1, 5)


def cooldown_medium(interaction: discord.Interaction[LatteBot]) -> Cooldown | None:
    if interaction.user == interaction.client.owner:
        return None
    return Cooldown(1, 10)


def cooldown_long(interaction: discord.Interaction[LatteBot]) -> Cooldown | None:
    if interaction.user == interaction.client.owner:
        return None
    return Cooldown(1, 20)


def custom_cooldown(interaction: discord.Interaction[LatteBot], rate: float, per: float) -> Cooldown | None:
    if interaction.user == interaction.client.owner:
        return None
    return Cooldown(rate, per)
