from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any, Self

import discord
from discord import Interaction, ui
from discord.ext import commands

if TYPE_CHECKING:
    from discord import InteractionMessage, Message

    from lattebot.core.bot import LatteBot


_log = logging.getLogger(__name__)


class View(ui.View):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._message: Message | InteractionMessage | None = None

    def reset_timeout(self) -> None:
        self.timeout = self.timeout

    async def _scheduled_task(self, item: discord.ui.Item[Self], interaction: Interaction[LatteBot]) -> None:  # type: ignore[override]
        try:
            item._refresh_state(interaction, interaction.data)  # type: ignore[arg-type]

            allow = await item.interaction_check(interaction) and await self.interaction_check(interaction)
            if not allow:
                return await self.on_check_failure(interaction)

            if self.timeout:
                self.__timeout_expiry = time.monotonic() + self.timeout

            await item.callback(interaction)
        except Exception as e:  # noqa: BLE001
            return await self.on_error(interaction, e, item)

    async def on_error(self, interaction: Interaction[LatteBot], error: Exception, item: ui.Item[Any]) -> None:  # type: ignore[override]
        interaction.client.dispatch('view_error', interaction, error, item)

    # --- code from pycord ---

    async def on_check_failure(self, interaction: Interaction[LatteBot]) -> None:
        """|coro|
        A callback that is called when a :meth:`View.interaction_check` returns ``False``.
        This can be used to send a response when a check failure occurs.

        Parameters
        ----------
        interaction: :class:`~discord.Interaction`
            The interaction that occurred.
        """  # noqa: D205

    def disable_all_items(self, *, exclusions: list[ui.Button[Self] | ui.Select[Self]] | None = None) -> None:
        """
        Disables all items in the view.

        Parameters
        ----------
        exclusions: Optional[List[:class:`Item`]]
            A list of items in `self.children` to not disable from the view.
        """
        for child in self.children:
            if isinstance(child, ui.Button | ui.Select) and exclusions and child in exclusions:
                child.disabled = True

    def enable_all_items(self, *, exclusions: list[ui.Button[Self] | ui.Select[Self]] | None = None) -> None:
        """
        Enables all items in the view.

        Parameters
        ----------
        exclusions: Optional[List[:class:`Item`]]
            A list of items in `self.children` to not enable from the view.
        """  # noqa: D401
        for child in self.children:
            if isinstance(child, ui.Button | ui.Select) and exclusions and child in exclusions:
                child.disabled = False

    # ---

    @property
    def message(self) -> Message | InteractionMessage | None:
        return self._message

    @message.setter
    def message(self, value: Message | InteractionMessage | None) -> None:
        self._message = value

    # -

    def add_url_button(
        self,
        label: str,
        url: str,
        *,
        emoji: str | discord.Emoji | discord.PartialEmoji | None = None,
        disabled: bool = False,
        row: int | None = None,
    ) -> Self:
        """
        Add a url button to the view.

        Parameters
        ----------
        label: str
            The label of the button.
        url: str
            The url of the button.
        disabled: bool
            Whether the button is disabled or not.
        row: int | None
            The row of the button.
        emoji: str | :class:`~discord.Emoji` | :class:`~discord.PartialEmoji` | None
            The emoji of the button.
        """
        self.add_item(ui.Button(label=label, url=url, emoji=emoji, disabled=disabled, row=row))
        return self


class URLButtonView(ui.View):
    def __init__(
        self,
        label: str,
        url: str,
        *,
        emoji: str | None = None,
        disabled: bool = False,
        row: int | None = None,
    ) -> None:
        super().__init__()
        self.add_item(ui.Button(label=label, url=url, emoji=emoji, disabled=disabled, row=row))


def key(interaction: discord.Interaction) -> discord.User | discord.Member:
    return interaction.user


# thank for stellabot
class ViewAuthor(View):
    def __init__(self, interaction: Interaction[LatteBot], *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.interaction: Interaction[LatteBot] = interaction
        self.locale: discord.Locale = interaction.locale
        self.bot: LatteBot = interaction.client
        self._author: discord.Member | discord.User = interaction.user
        # self.is_command = interaction.command is not None
        self.cooldown = commands.CooldownMapping.from_cooldown(4.0, 12.0, key)

    async def before_callback(self, interaction: Interaction[LatteBot]) -> None:
        if self.locale == interaction.locale:
            return
        self.locale = interaction.locale

    async def interaction_check(self, interaction: Interaction[LatteBot]) -> bool:  # type: ignore[override]
        """Only allowing the context author to interact with the view."""
        user = interaction.user

        if await self.bot.is_owner(user):
            return True

        # if isinstance(user, discord.Member) and user.guild_permissions.administrator:
        #     return True

        if user != self.author:
            bucket = self.cooldown.get_bucket(interaction)
            if bucket and not bucket.update_rate_limit():
                ...
                # bucket.get_retry_after()
                # TODO: custom cooldown message

            return False

        return True

    @property
    def author(self) -> discord.Member | discord.User:
        return self._author

    @author.setter
    def author(self, value: discord.Member | discord.User) -> None:
        self._author = value
