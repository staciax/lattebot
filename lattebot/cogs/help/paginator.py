# https://github.com/Rapptz/RoboDanny/blob/rewrite/cogs/utils/paginator.py

from __future__ import annotations

import traceback
from typing import TYPE_CHECKING, Any, Self

import discord
from discord import ui
from discord.utils import MISSING

if TYPE_CHECKING:
    from lattebot.core.bot import LatteBot


class NumberedPageModal(ui.Modal, title='Go to page'):
    page = ui.TextInput(label='Page', placeholder='Enter a number', min_length=1)  # type: ignore[var-annotated]

    def __init__(self, max_pages: int | None) -> None:
        super().__init__()
        self.interaction: discord.Interaction[LatteBot] | None = None
        if max_pages is not None:
            as_string = str(max_pages)
            self.page.placeholder = f'Enter a number between 1 and {as_string}'
            self.page.max_length = len(as_string)

    async def on_submit(self, interaction: discord.Interaction[LatteBot]) -> None:  # type: ignore[override]
        self.interaction = interaction
        self.stop()


class PageSource:
    """An interface representing a menu page's data source for the actual menu page.
    Subclasses must implement the backing resource along with the following methods:
    - :meth:`get_page`
    - :meth:`is_paginating`
    - :meth:`format_page`.
    """  # noqa: D205

    async def _prepare_once(self) -> None:
        try:
            # Don't feel like formatting hasattr with
            # the proper mangling
            # read this as follows:
            # if hasattr(self, '__prepare')
            # except that it works as you expect
            self.__prepare  # type: ignore[has-type] # noqa: B018
        except AttributeError:
            await self.prepare()
            self.__prepare = True

    async def prepare(self) -> None:
        """|coro|
        A coroutine that is called after initialisation
        but before anything else to do some asynchronous set up
        as well as the one provided in ``__init__``.
        By default this does nothing.
        This coroutine will only be called once.
        """  # noqa: D205
        return

    def is_paginating(self) -> bool:
        """An abstract method that notifies the :class:`MenuPages` whether or not
        to start paginating. This signals whether to add reactions or not.
        Subclasses must implement this.

        Returns
        -------
        :class:`bool`
            Whether to trigger pagination.
        """  # noqa: D205, D401
        raise NotImplementedError

    def get_max_pages(self) -> int | None:
        """An optional abstract method that retrieves the maximum number of pages
        this page source has. Useful for UX purposes.
        The default implementation returns ``None``.

        Returns
        -------
        Optional[:class:`int`]
            The maximum number of pages required to properly
            paginate the elements, if given.
        """  # noqa: D205, D401
        return None

    async def get_page(self, page_number: int) -> Any:
        """|coro|
        An abstract method that retrieves an object representing the object to format.
        Subclasses must implement this.
        .. note::
            The page_number is zero-indexed between [0, :meth:`get_max_pages`),
            if there is a maximum number of pages.

        Parameters
        ----------
        page_number: :class:`int`
            The page number to access.

        Returns
        -------
        Any
            The object represented by that page.
            This is passed into :meth:`format_page`.
        """  # noqa: D205
        raise NotImplementedError

    async def format_page(self, menu: Any, page: Any) -> discord.Embed | str | dict[Any, Any]:
        """|maybecoro|
        An abstract method to format the page.
        This method must return one of the following types.
        If this method returns a ``str`` then it is interpreted as returning
        the ``content`` keyword argument in :meth:`discord.Message.edit`
        and :meth:`discord.abc.Messageable.send`.
        If this method returns a :class:`discord.Embed` then it is interpreted
        as returning the ``embed`` keyword argument in :meth:`discord.Message.edit`
        and :meth:`discord.abc.Messageable.send`.
        If this method returns a ``dict`` then it is interpreted as the
        keyword-arguments that are used in both :meth:`discord.Message.edit`
        and :meth:`discord.abc.Messageable.send`. The two of interest are
        ``embed`` and ``content``.

        Parameters
        ----------
        menu: :class:`Menu`
            The menu that wants to format this page.
        page: Any
            The page returned by :meth:`PageSource.get_page`.

        Returns
        -------
        Union[:class:`str`, :class:`discord.Embed`, :class:`dict`]
            See above.
        """  # noqa: D205
        raise NotImplementedError


class ListPageSource[T](PageSource):
    """A data source for a sequence of items.
    This page source does not handle any sort of formatting, leaving it up
    to the user. To do so, implement the :meth:`format_page` method.

    Attributes
    ----------
    entries: Sequence[Any]
        The sequence of items to paginate.
    per_page: :class:`int`
        How many elements are in a page.
    """  # noqa: D205

    def __init__(self, entries: list[T], per_page: int = 12) -> None:
        self.entries = entries
        self.per_page = per_page

        pages, left_over = divmod(len(entries), per_page)
        if left_over:
            pages += 1

        self._max_pages = pages

    def is_paginating(self) -> bool:
        """:class:`bool`: Whether pagination is required."""
        return len(self.entries) > self.per_page

    def get_max_pages(self) -> int:
        """:class:`int`: The maximum number of pages required to paginate this sequence."""
        return self._max_pages

    async def get_page(self, page_number: int) -> Any | list[Any]:
        """Returns either a single element of the sequence or
        a slice of the sequence.
        If :attr:`per_page` is set to ``1`` then this returns a single
        element. Otherwise it returns at most :attr:`per_page` elements.

        Returns
        -------
        Union[Any, List[Any]]
            The data returned.
        """  # noqa: D205, D401
        if self.per_page == 1:
            return self.entries[page_number]
        base = page_number * self.per_page
        return self.entries[base : base + self.per_page]


class LattePages(ui.View):
    def __init__(
        self,
        source: PageSource = MISSING,
        *,
        interaction: discord.Interaction[LatteBot] = MISSING,
        check_embeds: bool = True,
        compact: bool = False,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.source: PageSource = source
        self.check_embeds: bool = check_embeds
        if hasattr(self, 'interaction') and interaction is not MISSING:
            self.interaction = interaction
        else:
            self.interaction = MISSING
        self.message: discord.Message | None = None
        self.current_page: int = 0
        self.compact: bool = compact
        self.clear_items()
        if self.source is not MISSING:
            self.__prepare = True
            self.fill_items()

    def fill_items(self) -> None:
        if not self.compact:
            self.numbered_page.row = 1
            self.stop_pages.row = 1

        if self.source.is_paginating():
            max_pages = self.source.get_max_pages()
            use_last_and_first = max_pages is not None and max_pages >= 2  # noqa: PLR2004
            if use_last_and_first:
                self.add_item(self.go_to_first_page)
            self.add_item(self.go_to_previous_page)
            if not self.compact:
                self.add_item(self.go_to_current_page)
            self.add_item(self.go_to_next_page)
            if use_last_and_first:
                self.add_item(self.go_to_last_page)
            if not self.compact:
                self.add_item(self.numbered_page)
            self.add_item(self.stop_pages)

    async def _get_kwargs_from_page(self, page: int) -> dict[str, Any]:
        value = await discord.utils.maybe_coroutine(self.source.format_page, self, page)  # type: ignore[var-annotated, arg-type]
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            return {'content': value, 'embed': None}
        if isinstance(value, discord.Embed):
            return {'embed': value, 'content': None}
        if isinstance(value, list) and all(isinstance(v, discord.Embed) for v in value):
            return {'embeds': value, 'content': None}
        return {}

    async def show_page(self, interaction: discord.Interaction, page_number: int) -> None:
        page = await self.source.get_page(page_number)
        self.current_page = page_number
        kwargs = await self._get_kwargs_from_page(page)
        self._update_labels(page_number)
        if kwargs:
            if interaction.response.is_done():
                if self.message:
                    await self.message.edit(**kwargs, view=self)
            else:
                await interaction.response.edit_message(**kwargs, view=self)

    def _update_labels(self, page_number: int) -> None:
        self.go_to_first_page.disabled = page_number == 0
        if self.compact:
            max_pages = self.source.get_max_pages()
            self.go_to_last_page.disabled = max_pages is None or (page_number + 1) >= max_pages
            self.go_to_next_page.disabled = max_pages is not None and (page_number + 1) >= max_pages
            self.go_to_previous_page.disabled = page_number == 0
            return

        self.go_to_current_page.label = str(page_number + 1)
        self.go_to_previous_page.label = str(page_number)
        self.go_to_next_page.label = str(page_number + 2)
        self.go_to_next_page.disabled = False
        self.go_to_previous_page.disabled = False
        self.go_to_first_page.disabled = False

        max_pages = self.source.get_max_pages()
        if max_pages is not None:
            self.go_to_last_page.disabled = (page_number + 1) >= max_pages
            if (page_number + 1) >= max_pages:
                self.go_to_next_page.disabled = True
                self.go_to_next_page.label = '…'
            if page_number == 0:
                self.go_to_previous_page.disabled = True
                self.go_to_previous_page.label = '…'

    async def show_checked_page(self, interaction: discord.Interaction, page_number: int) -> None:
        max_pages = self.source.get_max_pages()
        try:
            if max_pages is None:
                # If it doesn't give maximum pages, it cannot be checked
                await self.show_page(interaction, page_number)
            elif max_pages > page_number >= 0:
                await self.show_page(interaction, page_number)
        except IndexError:
            # An error happened that can be handled, so ignore it.
            pass

    async def interaction_check(self, interaction: discord.Interaction[LatteBot]) -> bool:  # type: ignore[override]
        if interaction.user and interaction.user in {self.interaction.client, self.interaction.user}:
            return True
        await interaction.response.send_message(
            'This pagination menu cannot be controlled by you, sorry!', ephemeral=True
        )
        return False

    async def on_timeout(self) -> None:
        if self.message:
            await self.message.edit(view=None)

    async def on_error(
        self,
        interaction: discord.Interaction[LatteBot],  # type: ignore[override]
        error: Exception,
        _item: ui.Item[Self],
    ) -> None:
        if interaction.response.is_done():
            await interaction.followup.send('An unknown error occurred, sorry', ephemeral=True)
        else:
            await interaction.response.send_message('An unknown error occurred, sorry', ephemeral=True)

        try:
            exc = ''.join(traceback.format_exception(type(error), error, error.__traceback__, chain=False))
            embed = discord.Embed(
                title=f'{self.source.__class__.__name__} Error',
                description=f'```py\n{exc}\n```',
                timestamp=interaction.created_at,
                colour=0xCC3366,
            )
            embed.add_field(name='User', value=f'{interaction.user} ({interaction.user.id})')
            embed.add_field(name='Guild', value=f'{interaction.guild} ({interaction.guild_id})')
            embed.add_field(name='Channel', value=f'{interaction.channel} ({interaction.channel_id})')

            # TODO: send to stats webhook
            # await self.interaction.client.stats_webhook.send(embed=embed)
        except discord.HTTPException:
            pass

    async def start(self, page_number: int = 0, *, content: str | None = None, ephemeral: bool = False) -> None:
        if self.check_embeds and not self.interaction.channel.permissions_for(self.interaction.guild.me).embed_links:  # type: ignore[union-attr]
            # TODO: handle this case better send or followup
            await self.interaction.response.send_message(
                'Bot does not have embed links permission in this channel.', ephemeral=True
            )
            return
        self.current_page = page_number

        try:
            self.__prepare  # noqa: B018
        except AttributeError:
            self.fill_items()
            self.__prepare = True

        await self.source._prepare_once()
        page = await self.source.get_page(page_number)
        kwargs = await self._get_kwargs_from_page(page)
        if content:
            kwargs.setdefault('content', content)

        self._update_labels(page_number)
        if self.message is not None:
            await self.message.edit(**kwargs, view=self)
            return
        if self.interaction.response.is_done():
            self.message = await self.interaction.followup.send(**kwargs, view=self, ephemeral=ephemeral)
        else:
            await self.interaction.response.send_message(**kwargs, view=self, ephemeral=ephemeral)
            self.message = await self.interaction.original_response()

    @ui.button(label='≪', style=discord.ButtonStyle.grey)
    async def go_to_first_page(self, interaction: discord.Interaction[LatteBot], _button: ui.Button[Self]) -> None:
        """Go to the first page."""
        await self.show_page(interaction, 0)

    @ui.button(label='Back', style=discord.ButtonStyle.blurple)
    async def go_to_previous_page(self, interaction: discord.Interaction[LatteBot], _button: ui.Button[Self]) -> None:
        """Go to the previous page."""
        await self.show_checked_page(interaction, self.current_page - 1)

    @ui.button(label='Current', style=discord.ButtonStyle.grey, disabled=True)
    async def go_to_current_page(self, interaction: discord.Interaction, button: ui.Button[Self]) -> None:
        pass

    @ui.button(label='Next', style=discord.ButtonStyle.blurple)
    async def go_to_next_page(self, interaction: discord.Interaction[LatteBot], _button: ui.Button[Self]) -> None:
        """Go to the next page."""
        await self.show_checked_page(interaction, self.current_page + 1)

    @ui.button(label='≫', style=discord.ButtonStyle.grey)
    async def go_to_last_page(self, interaction: discord.Interaction[LatteBot], _button: ui.Button[Self]) -> None:
        """Go to the last page."""
        # The call here is safe because it's guarded by skip_if
        await self.show_page(interaction, self.source.get_max_pages() - 1)  # type: ignore[operator]

    @ui.button(label='Skip to page...', style=discord.ButtonStyle.grey)
    async def numbered_page(self, interaction: discord.Interaction[LatteBot], _button: ui.Button[Self]) -> None:
        """Lets you type a page number to go to."""
        if self.message is None:
            return

        modal = NumberedPageModal(self.source.get_max_pages())
        await interaction.response.send_modal(modal)
        timed_out = await modal.wait()

        if timed_out:
            await interaction.followup.send('Took too long', ephemeral=True)
            return

        if modal.interaction is None:
            return

        if self.is_finished():
            await modal.interaction.response.send_message('Took too long', ephemeral=True)
            return

        value = str(modal.page.value)
        if not value.isdigit():
            await modal.interaction.response.send_message(f'Expected a number not {value!r}', ephemeral=True)
            return

        page_number = int(value)
        await self.show_checked_page(modal.interaction, page_number - 1)
        if not modal.interaction.response.is_done():
            # assert modal.page.placeholder is not None
            page_placeholder = modal.page.placeholder
            if page_placeholder is None:
                return
            error = page_placeholder.replace('Enter', 'Expected')
            await modal.interaction.response.send_message(error, ephemeral=True)

    @ui.button(label='Quit', style=discord.ButtonStyle.red)
    async def stop_pages(self, interaction: discord.Interaction[LatteBot], _button: ui.Button[Self]) -> None:
        """Stops the pagination session."""  # noqa: D401
        await interaction.response.defer()
        await interaction.delete_original_response()
        self.stop()
