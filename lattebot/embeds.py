from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING, Any, Literal, Self, TypeIs, override

import discord
from discord import app_commands

__all__ = (
    'DarkEmbed',
    'Embed',
    'ErrorEmbed',
    'LocalizedEmbed',
    'SuccessEmbed',
    'WarningEmbed',
)

if TYPE_CHECKING:
    from collections.abc import Iterable
    from datetime import datetime

    from discord.types.embed import EmbedType

    from lattebot.core.translator import Translator


type LocaleStr = str | app_commands.locale_str


def is_locale_str(value: Any) -> TypeIs[app_commands.locale_str]:
    return isinstance(value, app_commands.locale_str)


class Embed(discord.Embed):
    def __init__(  # noqa: PLR0913
        self,
        *,
        colour: int | discord.Colour | None = 0xFFFFFF,
        color: int | discord.Colour | None = 0xFFFFFF,
        title: Any | None = None,
        type: EmbedType = 'rich',  # noqa: A002
        url: Any | None = None,
        description: Any | None = None,
        timestamp: datetime | None = None,
        fields: Iterable[
            tuple[LocaleStr, LocaleStr, bool] | tuple[LocaleStr, LocaleStr] | Literal['blank', 'blank_inline'],
        ] = (),
        **kwargs: Any,
    ) -> None:
        super().__init__(
            color=color,
            colour=colour,
            title=title,
            type=type,
            description=description,
            url=url,
            timestamp=timestamp,
        )
        self.extra: dict[str, Any] = kwargs
        for field in fields:
            if isinstance(field, tuple):
                name, value, *inline = field
                self.add_field(name=name, value=value, inline=inline[0] if inline else True)
            elif field in ('blank', 'blank_inline'):  # noqa: PLR6201
                self.add_empty_field(inline=field == 'blank_inline')

    def set_empty_title(self) -> Self:
        self.title = '\u200b'
        return self

    def add_empty_field(self, *, inline: bool = False) -> Self:
        self.add_field(name='\u200b', value='\u200b', inline=inline)
        return self

    def success(self) -> Self:
        self.colour = 0x8BE28B  # type: ignore[assignment]
        return self

    def error(self) -> Self:
        self.colour = 0xFF6961  # type: ignore[assignment]
        return self

    def warning(self) -> Self:
        self.colour = 0xFDFD96  # type: ignore[assignment]
        return self

    def dark(self) -> Self:
        self.colour = 0x0F1923  # type: ignore[assignment]
        return self


SuccessEmbed = partial(Embed, colour=0x8BE28B)
ErrorEmbed = partial(Embed, colour=0xFF6961)
WarningEmbed = partial(Embed, colour=0xFDFD96)
DarkEmbed = partial(Embed, colour=0x0F1923)


class LocalizedEmbed(Embed):
    def __init__(  # noqa: PLR0913
        self,
        translator: Translator,
        locale: discord.Locale,
        *,
        colour: int | discord.Colour | None = 0xFFFFFF,
        color: int | discord.Colour | None = 0xFFFFFF,
        title: Any | None = None,
        type: EmbedType = 'rich',  # noqa: A002
        url: Any | None = None,
        description: Any | None = None,
        timestamp: datetime | None = None,
        fields: Iterable[
            tuple[LocaleStr, LocaleStr, bool] | tuple[LocaleStr, LocaleStr] | Literal['blank', 'blank_inline'],
        ] = (),
        **kwargs: Any,
    ) -> None:
        title_translated = translator.translate_text(title, locale) if is_locale_str(title) else title
        description_translated = (
            translator.translate_text(description, locale) if is_locale_str(description) else description
        )
        super().__init__(
            color=color,
            colour=colour,
            title=title_translated,
            type=type,
            description=description_translated,
            url=url,
            timestamp=timestamp,
            fields=fields,
            kwargs=kwargs,
        )
        self.locale = locale
        self.translator = translator

    def set_title(self, value: Any) -> Self:
        self.title = self.translator.translate_text(value, self.locale) if is_locale_str(value) else str(value)
        return self

    def set_description(self, value: Any) -> Self:
        self.description = self.translator.translate_text(value, self.locale) if is_locale_str(value) else str(value)
        return self

    @override
    def add_field(self, *, name: Any, value: Any, inline: bool = True) -> Self:
        if is_locale_str(name):
            name = self.translator.translate_text(name, self.locale)
        if is_locale_str(value):
            value = self.translator.translate_text(value, self.locale)
        return super().add_field(name=name, value=value, inline=inline)

    @override
    def set_author(self, *, name: Any, url: Any | None = None, icon_url: Any | None = None) -> Self:
        if is_locale_str(name):
            name = self.translator.translate_text(name, self.locale)
        return super().set_author(name=name, url=url, icon_url=icon_url)

    @override
    def set_footer(self, *, text: Any | None = None, icon_url: Any | None = None) -> Self:
        if is_locale_str(text):
            text = self.translator.translate_text(text, self.locale)
        return super().set_footer(text=text, icon_url=icon_url)

    @override
    def insert_field_at(self, index: int, *, name: Any, value: Any, inline: bool = True) -> Self:
        if is_locale_str(name):
            name = self.translator.translate_text(name, self.locale)
        if is_locale_str(value):
            value = self.translator.translate_text(value, self.locale)
        return super().insert_field_at(index, name=name, value=value, inline=inline)

    @override
    def set_field_at(self, index: int, *, name: Any, value: Any, inline: bool = True) -> Self:
        if is_locale_str(name):
            name = self.translator.translate_text(name, self.locale)
        if is_locale_str(value):
            value = self.translator.translate_text(value, self.locale)
        return super().set_field_at(index, name=name, value=value, inline=inline)
