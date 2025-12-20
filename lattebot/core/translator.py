from __future__ import annotations

import asyncio
import contextlib
import inspect
import logging
from functools import reduce
from typing import TYPE_CHECKING, Any, Literal, overload

from anyio import Path
from discord import Locale
from discord.app_commands.commands import Command, ContextMenu, Group, Parameter
from discord.app_commands.models import Choice
from discord.app_commands.translator import (
    TranslationContext,
    TranslationContextLocation,
    Translator as _Translator,
    locale_str,
)
from pydantic import BaseModel as PydanticBaseModel, ConfigDict

from lattebot.utils import read_yaml, save_yaml

__all__ = ('Translator',)

if TYPE_CHECKING:
    from discord.app_commands.translator import OtherTranslationContext, TranslationContextTypes
    from discord.ext.commands import Cog

    from .bot import LatteBot

    type Translatable = Command[Any, ..., Any] | Group | ContextMenu | Parameter | Choice[Any]

log = logging.getLogger('latte.translator')


class BaseModel(PydanticBaseModel):
    model_config = ConfigDict(
        extra='forbid',
        # frozen=True,
        # populate_by_name=True,
        # validate_assignment=True,
    )


class OptionModel(BaseModel):
    display_name: str
    description: str
    choices: dict[str, str] | None = None


class AppCommandModel(BaseModel):
    # name: Annotated[str, Field(min_length=1, max_length=32)]
    name: str
    description: str
    options: dict[str, OptionModel] | None = None


def _build_app_command_model(
    app_command: Command[Any, ..., Any] | Group,
    empty_fields: bool = False,
) -> AppCommandModel:
    """Convert an application command or group into an AppCommand model.

    If empty_fields is True, the fields will be empty strings.
    """
    name: str = '' if empty_fields else app_command.name
    description: str = '' if empty_fields else app_command.description
    options: dict[str, OptionModel] | None = None

    if isinstance(app_command, Command) and app_command.parameters:
        options = {
            param.name: OptionModel(
                display_name='' if empty_fields else param.display_name,
                description='' if empty_fields else param.description,
                choices=(
                    {str(choice.value): '' if empty_fields else choice.name for choice in param.choices}
                    if param.choices
                    else None
                ),
            )
            for param in app_command.parameters
        }

    return AppCommandModel(
        name=name,
        description=description,
        options=options,
    )


def _update_app_command_model(model: AppCommandModel, update_model: AppCommandModel) -> AppCommandModel:
    """Update the fields of an existing AppCommand model with the fields from another AppCommand model."""
    original_data = model.model_dump()
    new_data = update_model.model_dump()

    def deep_update(data: dict[str, Any], update: dict[str, Any]) -> None:
        for key in set(update).intersection(data):
            if isinstance(data[key], dict):
                deep_update(data[key], update[key])
            else:
                data[key] = update[key]

    deep_update(original_data, new_data)

    # return AppCommand.model_copy(update=data1)
    return AppCommandModel.model_validate(original_data)  # NOTE: avoid pydantic serializer warnings


# utils


async def _get_cog_locales_path(cog: Cog) -> Path | None:
    module = inspect.getmodule(cog)
    if module is None:
        log.warning('No module found for cog %s', cog.qualified_name)
        # raise ModuleNotFoundError(f'No module found for cog {cog.qualified_name}')
        return None

    module_file_path = Path(inspect.getfile(module))
    module_path = module_file_path.parent
    locales_path = module_path / 'locales'

    if not await locales_path.exists():
        log.warning('No locales folder found for cog %s', cog.qualified_name)
        # raise FileNotFoundError(f'No locales folder found for cog {cog.qualified_name}')
        return None

    return locales_path


async def _ensure_locale_directory(cog_locales_path: Path, locale: Locale) -> Path:
    locale_code = locale.value.replace('-', '_')
    locale_dir = cog_locales_path / locale_code
    if not await locale_dir.exists():
        await locale_dir.mkdir(parents=True, exist_ok=True)
    return locale_dir


def _get_app_commands_data(
    cog: Cog,
    *,
    exclude_none: bool = True,
    empty_fields: bool = False,
) -> dict[str, dict[str, Any]]:
    return {
        command.qualified_name: _build_app_command_model(command, empty_fields=empty_fields).model_dump(
            exclude_none=exclude_none
        )
        for command in cog.walk_app_commands()
    }


def _update_app_commands_data(cog: Cog, locale_data: dict[str, Any]) -> dict[str, Any]:
    updated_data = {}
    for command in cog.walk_app_commands():
        command_name = command.qualified_name
        command_model = _build_app_command_model(command)

        if command_name in locale_data:
            existing_model = AppCommandModel.model_validate(locale_data[command_name])
            updated_model = _update_app_command_model(
                command_model,
                existing_model,
            )
            updated_data[command_name] = updated_model.model_dump(exclude_none=True)
        else:
            updated_data[command_name] = command_model.model_dump(exclude_none=True)
    return updated_data


# TODO: remove duplicate code

# TODO: investigate the new string formatting features in Python 3.14
# https://docs.python.org/3/whatsnew/3.14.html
# PEP 750: Template string literals
# i think template string literals would be a good fit for this use case


class AppCommandTranslator:
    __slots__ = (
        '__current_command',
        '__current_parameter',
        '_translations',
        'translator',
    )

    # NOTE: temporarily store the current command and parameter being processed
    __current_command: Command[Any, ..., Any] | Group | ContextMenu
    __current_parameter: Parameter

    def __init__(self, translator: Translator) -> None:
        self.translator = translator
        self._translations: dict[str, dict[str, Any]] = {}

    async def clear(self) -> None:
        self._translations.clear()
        log.info('cleared app command translations.')

    def reset_context(self) -> None:
        with contextlib.suppress(AttributeError):
            del self.__current_command
            del self.__current_parameter

    def get_translations(self, locale: Locale) -> dict[str, str] | None:
        return self._translations.get(locale.value)

    async def translate(self, string: locale_str, locale: Locale, context: TranslationContextTypes) -> str | None:
        if context.location == TranslationContextLocation.other:
            return None

        if (locale == self.translator.default_locale) or (locale not in self.translator.locales):
            return None

        # if isinstance(context.data, ContextMenu):
        #     return None

        keys = self._get_translation_keys(context)

        if not keys:
            log.warning(
                'Translation keys not found for message %r in locale %r, location %r.',
                string.message,
                locale.value,
                context.location.name,
            )
            return None

        locale_translations = self.get_translations(locale)

        if not locale_translations:
            # binding = context.data.binding if hasattr(context.data, 'binding') else None
            log.warning(
                'Translations not found for locale %r in location %r, message %r.',
                locale.value,
                context.location.name,
                string.message,
                # repr(binding),
            )
            return None

        translated_string = self._get_string_by_keys(locale_translations, keys)

        if not translated_string:
            log.warning(
                'Translation not found for message %r in locale %r, location %r',
                string.message,
                locale.value,
                context.location.name,
            )
            return None

        return translated_string

    async def load_locale_data(
        self,
        locale: Locale,
        locale_dir: Path,
        cog: Cog,
    ) -> None:
        is_default_locale = locale == self.translator.default_locale
        locale_file = locale_dir / 'app_command.yaml'

        if not await locale_file.exists():
            await locale_file.touch()

        locale_data: dict[str, Any] | None = await read_yaml(locale_file)

        if locale_data is None:
            commands_data = _get_app_commands_data(cog, empty_fields=not is_default_locale)
        else:
            commands_data = _update_app_commands_data(cog, locale_data)

        if not commands_data:
            return

        if locale.value not in self._translations:
            self._translations[locale.value] = commands_data
        else:
            self._translations[locale.value].update(commands_data)

        await save_yaml(locale_file, commands_data, overwrite=True)

    def _get_string_by_keys(self, data: dict[str, Any], keys: list[str]) -> str | None:
        try:
            value = reduce(lambda d, k: d[k], keys, data)
            if isinstance(value, str):
                return value
            log.error('Value for keys "%s" is not a string.', ' -> '.join(keys))
        except KeyError, TypeError:
            log.exception('Failed to retrieve value by keys "%s".', ' -> '.join(keys))

        return None

    def _get_translation_keys(self, context: TranslationContextTypes) -> list[str]:
        keys = []

        context_location = context.location
        translatable = context.data

        if context_location in {
            TranslationContextLocation.command_name,
            TranslationContextLocation.group_name,
        } and isinstance(translatable, Command | Group | ContextMenu):
            keys.extend([translatable.qualified_name, 'name'])
            self.__current_command = translatable

        elif context_location in {
            TranslationContextLocation.command_description,
            TranslationContextLocation.group_description,
        } and isinstance(translatable, Command | Group):
            keys.extend([translatable.qualified_name, 'description'])

        elif context_location == TranslationContextLocation.parameter_name and isinstance(translatable, Parameter):
            keys.extend([
                translatable.command.qualified_name,
                'options',
                translatable.name,
                'display_name',
            ])
            self.__current_parameter = translatable

        elif context_location == TranslationContextLocation.parameter_description and isinstance(
            translatable, Parameter
        ):
            keys.extend([
                translatable.command.qualified_name,
                'options',
                translatable.name,
                'description',
            ])

        elif context_location == TranslationContextLocation.choice_name and isinstance(translatable, Choice):
            with contextlib.suppress(AttributeError):
                keys.extend([
                    self.__current_command.qualified_name,
                    'options',
                    self.__current_parameter.name,
                    'choices',
                    str(translatable.value),
                ])

        return keys


class TextTranslator:
    __slots__ = (
        '_translations',
        'translator',
    )

    def __init__(self, translator: Translator) -> None:
        self.translator = translator
        self._translations: dict[str, dict[str, str]] = {}

    async def clear(self) -> None:
        self._translations.clear()
        log.info('cleared text translations.')

    def get_translations(self, locale: Locale) -> dict[str, str] | None:
        return self._translations.get(locale.value)

    def translate(
        self,
        string: locale_str,
        locale: Locale,
        _context: TranslationContextTypes | None = None,
    ) -> str:
        translations = self.get_translations(locale) or self.get_translations(self.translator.default_locale)

        if not translations:
            log.warning('Translation not found for text: "%s" in locale: %s', string.message, locale.value)
            return string.message

        text_translated = translations.get(string.message)

        if text_translated:
            text_translated = text_translated.format(**string.extras)

        return text_translated or string.message

    async def load_locale_data(self, locale: Locale, locale_dir: Path) -> None:
        locale_file = locale_dir / 'text.yaml'

        if not await locale_file.exists():
            await locale_file.touch()

        locale_data: dict[str, Any] | None = await read_yaml(locale_file)

        if not locale_data:
            return

        if locale.value not in self._translations:
            self._translations[locale.value] = locale_data
        else:
            self._translations[locale.value].update(locale_data)


class Translator(_Translator):
    __slots__ = (
        '_loading_task',
        'app_command_translator',
        'bot',
        'default_locale',
        'locales',
        'text_translator',
    )

    def __init__(
        self,
        bot: LatteBot,
        *,
        locales: tuple[Locale, ...] | None = None,
        default_locale: Locale = Locale.american_english,
    ) -> None:
        super().__init__()
        self.bot = bot
        if not locales:
            log.warning('No supported locales provided')
        self.default_locale = default_locale
        self.locales = {default_locale}
        if locales:
            self.locales.update(locales)

        self.app_command_translator = AppCommandTranslator(self)
        self.text_translator = TextTranslator(self)

        self._loading_task: asyncio.Task[None] | None = None

    async def load(self) -> None:
        # If already loading and not done, do nothing
        if self._loading_task is not None and not self._loading_task.done():
            return

        self._loading_task = self.bot.loop.create_task(self._load_locales_data(), name='translator-load_locales_data')

    async def unload(self) -> None:
        if self._loading_task and not self._loading_task.done():
            self._loading_task.cancel()
            try:
                await self._loading_task
            except asyncio.CancelledError:
                # Task cancellation is expected during unload; ignore but log for debugging.
                log.debug('translator load task was cancelled during unload')

        await self.app_command_translator.clear()
        await self.text_translator.clear()
        self._loading_task = None

        log.info('unloaded')

    def is_ready(self) -> bool:
        return bool(
            self._loading_task is not None and self._loading_task.done() and not self._loading_task.cancelled()
            # and self._loading_task.exception() is None
        )

    async def _load_locales_data(self) -> None:
        await self.bot.wait_until_ready()

        log.info('loading locales data...')

        # TODO: add support for loading translations from other sources such as global locales folder, etc.

        bot_cogs = self.bot.cogs.values()
        for cog in bot_cogs:
            cog_locales_path = await _get_cog_locales_path(cog)
            if not cog_locales_path:
                continue

            for locale in self.locales:
                locale_directory_path = await _ensure_locale_directory(cog_locales_path, locale)

                await self.text_translator.load_locale_data(locale, locale_directory_path)
                await self.app_command_translator.load_locale_data(locale, locale_directory_path, cog)

        log.info('locales data loaded.')

    @overload
    async def translate(self, string: locale_str, locale: Locale, context: OtherTranslationContext) -> str: ...

    @overload
    async def translate(self, string: locale_str, locale: Locale, context: TranslationContextTypes) -> str | None: ...

    async def translate(self, string: locale_str, locale: Locale, context: TranslationContextTypes) -> str | None:
        if context.location == TranslationContextLocation.other:
            return self.text_translator.translate(string, locale, context)

        return await self.app_command_translator.translate(string, locale, context)

    def translate_text(self, string: locale_str, locale: Locale, data: Any = None) -> str:
        context = TranslationContext[Literal[TranslationContextLocation.other], Any](
            location=TranslationContextLocation.other,
            data=data,
        )
        return self.text_translator.translate(string, locale, context)
