from __future__ import annotations

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
from pydantic import BaseModel

from lattebot.utils import read_yaml, save_yaml

__all__ = ('Translator',)

if TYPE_CHECKING:
    from discord.app_commands.translator import OtherTranslationContext, TranslationContextTypes
    from discord.ext.commands import Cog

    from .bot import LatteBot

    type Translatable = Command[Any, ..., Any] | Group | ContextMenu | Parameter | Choice[Any]

log = logging.getLogger('latte.translator')


class OptionModel(BaseModel):
    display_name: str
    description: str
    choices: dict[str, str] | None = None


class AppCommandModel(BaseModel):
    name: str
    description: str
    options: dict[str, OptionModel] | None = None


def build_app_command_model(app_command: Command[Any, ..., Any] | Group) -> AppCommandModel:
    """Convert an application command or group into an AppCommand model."""
    return AppCommandModel(
        name=app_command.name,
        description=app_command.description,
        options=(
            {
                param.name: OptionModel(
                    display_name=param.display_name,
                    description=param.description,
                    choices={str(choice.value): choice.name for choice in param.choices},
                )
                for param in app_command.parameters
            }
            if app_command.parameters
            else None
        )
        if isinstance(app_command, Command)
        else None,
    )


def build_empty_app_command_model(app_command: Command[Any, ..., Any] | Group) -> AppCommandModel:
    """Convert an application command or group into an AppCommand model with empty fields."""
    return AppCommandModel(
        name='',
        description='',
        options=(
            {
                param.name: OptionModel(
                    display_name='',
                    description='',
                    choices={str(choice.value): '' for choice in param.choices},
                )
                for param in app_command.parameters
            }
            if app_command.parameters
            else None
        )
        if isinstance(app_command, Command)
        else None,
    )


# TODO: unit test for update_app_command_model
def update_app_command_model(model: AppCommandModel, update_model: AppCommandModel) -> AppCommandModel:
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


async def get_cog_locales_path(cog: Cog) -> Path | None:
    cog_module = inspect.getmodule(cog)
    if cog_module is None:
        # log.warning('No module found for cog %s', cog.qualified_name)
        return None

    cog_file_path = inspect.getfile(cog_module)
    cog_directory = Path(cog_file_path).parent
    locales_path = cog_directory / 'locales'

    if not await locales_path.exists():
        # log.warning('No locales folder found for cog %s', cog.qualified_name)
        return None
    return locales_path


# TODO: remove duplicate code


class AppCommandTranslator:
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

    async def translate(self, string: locale_str, locale: Locale, context: TranslationContextTypes) -> str | None:  # noqa: PLR0911
        if context.location == TranslationContextLocation.other:
            return None

        if locale == self.translator.default_locale:
            return None

        if locale not in self.translator.locales:
            return None

        keys = self._get_translation_keys(context)

        if not keys:
            log.warning(
                'No translation keys found for message "%s" in locale "%s", location "%s", type "%s".',
                string.message,
                locale.value,
                context.location.name,
                type(context.data).__qualname__,
            )
            return None

        locale_translations = self._translations.get(locale.value)

        if not locale_translations:
            log.warning('No command translations available for locale "%s".', locale.value)
            return None

        translated_string = self._get_string_by_keys(locale_translations, keys)

        if not translated_string:
            log.warning(
                'Translation not found for message "%s" in locale "%s", location "%s", type "%s".',
                string.message,
                locale.value,
                context.location.name,
                type(context.data).__qualname__,
            )
            return None

        return translated_string

    async def load_from_cog(self, cog: Cog, locale: Locale, locale_dir: Path) -> None:
        is_default_locale = locale == self.translator.default_locale
        locale_file = locale_dir / 'app_command.yaml'

        if not await locale_file.exists():
            await locale_file.touch()

        locale_data: dict[str, Any] | None = await read_yaml(locale_file)

        if locale_data is None:
            commands_data = await self._get_app_commands_data(cog, empty_fields=not is_default_locale)
        else:
            commands_data = await self._update_app_commands_data(cog, locale_data)

        if not commands_data:
            return

        self._update_translation(locale, commands_data)
        await save_yaml(commands_data, locale_file)

    def _get_string_by_keys(self, data: dict[str, Any], keys: list[str]) -> str | None:
        try:
            value = reduce(lambda d, k: d[k], keys, data)
        except (KeyError, TypeError):
            log.exception('Failed to retrieve value by keys "%s".', ' -> '.join(keys))
        else:
            if isinstance(value, str):
                return value
            log.error('Value for keys "%s" is not a string.', ' -> '.join(keys))
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

    async def _get_app_commands_data(
        self,
        cog: Cog,
        *,
        exclude_none: bool = True,
        empty_fields: bool = False,
    ) -> dict[str, dict[str, Any]]:
        if empty_fields:
            return {
                command.qualified_name: build_empty_app_command_model(command).model_dump(exclude_none=exclude_none)
                for command in cog.walk_app_commands()
            }
        return {
            command.qualified_name: build_app_command_model(command).model_dump(exclude_none=exclude_none)
            for command in cog.walk_app_commands()
        }

    async def _update_app_commands_data(self, cog: Cog, locale_data: dict[str, Any]) -> dict[str, Any]:
        updated_data = {}
        for command in cog.walk_app_commands():
            command_name = command.qualified_name
            command_model = build_app_command_model(command)

            if command_name in locale_data:
                existing_model = AppCommandModel.model_validate(locale_data[command_name])
                updated_model = update_app_command_model(
                    command_model,
                    existing_model,
                )
                updated_data[command_name] = updated_model.model_dump(exclude_none=True)
            else:
                updated_data[command_name] = command_model.model_dump(exclude_none=True)
        return updated_data

    def _update_translation(
        self,
        locale: Locale,
        new_data: dict[str, Any],
    ) -> None:
        if locale.value not in self._translations:
            self._translations[locale.value] = new_data
        else:
            self._translations[locale.value].update(new_data)


class TextTranslator:
    def __init__(self, translator: Translator) -> None:
        self.translator = translator
        self._translations: dict[str, dict[str, str]] = {}

    async def clear(self) -> None:
        self._translations.clear()
        log.info('cleared text translations.')

    def translate(self, string: locale_str, locale: Locale, _context: TranslationContextTypes | None = None) -> str:
        locale_code = locale.value

        translations = self._translations.get(locale_code) or self._translations.get(locale_code)

        if not translations:
            log.warning('No text translations available for locale "%s".', locale.value)
            return string.message

        text_translated = translations.get(string.message)
        if text_translated is None:
            log.warning('Translation not found for text: "%s" in locale: %s', string.message, locale.value)

        return text_translated or string.message

    async def load_from_locale_dir(self, locale: Locale, locale_dir: Path) -> None:
        locale_file = locale_dir / 'text.yaml'

        if not await locale_file.exists():
            await locale_file.touch()

        locale_data: dict[str, Any] | None = await read_yaml(locale_file)

        if not locale_data:
            return

        self._update_translation(locale, locale_data)

    def _update_translation(
        self,
        locale: Locale,
        new_data: dict[str, Any],
    ) -> None:
        if locale.value not in self._translations:
            self._translations[locale.value] = new_data
        else:
            self._translations[locale.value].update(new_data)


class Translator(_Translator):
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

    async def load(self) -> None:
        # self.bot.loop.create_task(self.app_command_translator.load(), name='translator-app-command-load')
        # self.bot.loop.create_task(self.text_translator.load(), name='translator-text-load')
        self.bot.loop.create_task(self.initialize_translations(), name='translator-initialize-translations')
        log.info('loaded')

    async def unload(self) -> None:
        await self.app_command_translator.clear()
        await self.text_translator.clear()
        log.info('unloaded')

    # load_all_locale_files
    async def initialize_translations(self) -> None:
        await self.bot.wait_until_ready()

        bot_cogs = self.bot.cogs.values()
        for cog in bot_cogs:
            locales_path = await get_cog_locales_path(cog)
            if locales_path is None:
                log.warning('No locales folder found for cog %s', cog.qualified_name)
                continue

            for locale in self.locales:
                locale_code = locale.value.replace('-', '_')

                locale_dir = locales_path / locale_code
                if not await locale_dir.exists():
                    await locale_dir.mkdir(exist_ok=True)

                await self.text_translator.load_from_locale_dir(locale, locale_dir)
                await self.app_command_translator.load_from_cog(cog, locale, locale_dir)

    @overload
    async def translate(self, string: locale_str, locale: Locale, context: OtherTranslationContext) -> str: ...

    @overload
    async def translate(self, string: locale_str, locale: Locale, context: TranslationContextTypes) -> str | None: ...

    async def translate(self, string: locale_str, locale: Locale, context: TranslationContextTypes) -> str | None:
        tcl = context.location

        if tcl == TranslationContextLocation.other:
            return self.text_translator.translate(string, locale, context)

        return await self.app_command_translator.translate(string, locale, context)

    def translate_text(self, string: locale_str, locale: Locale, data: Any = None) -> str:
        context = TranslationContext[Literal[TranslationContextLocation.other], Any](
            location=TranslationContextLocation.other,
            data=data,
        )
        return self.text_translator.translate(string, locale, context)
