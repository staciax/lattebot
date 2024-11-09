from __future__ import annotations

import contextlib
import inspect
import logging
from functools import reduce
from typing import TYPE_CHECKING, Any

import yaml
from anyio import Path
from discord import Locale
from discord.app_commands.commands import Command, ContextMenu, Group, Parameter
from discord.app_commands.models import Choice
from discord.app_commands.translator import (
    TranslationContextLocation as TCL,  # noqa: N817
    Translator as _Translator,
    locale_str,
)
from pydantic import BaseModel

__all__ = ('Translator',)

if TYPE_CHECKING:
    from discord.app_commands.translator import (
        TranslationContextTypes,
    )
    from discord.ext.commands import Cog

    from .bot import LatteBot

    type Translatable = Command[Any, ..., Any] | Group | ContextMenu | Parameter | Choice[Any]

log = logging.getLogger('latte.translator')


class Option(BaseModel):
    display_name: str
    description: str
    choices: dict[str, str] | None = None


class AppCommand(BaseModel):
    name: str
    description: str
    options: dict[str, Option] | None = None


def get_app_command_model(app_command: Command[Any, ..., Any] | Group) -> AppCommand:
    return AppCommand(
        name=app_command.name,
        description=app_command.description,
        options=(
            {
                param.name: Option(
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


# TODO: unit test for update_app_command_model
def update_app_command_model(model: AppCommand, update_model: AppCommand) -> AppCommand:
    """
    Updates the fields of an existing AppCommand model with the fields from another AppCommand model.

    Parameters
    ----------
    model : AppCommand
        The original AppCommand model to be updated.
    update_model : AppCommand
        The AppCommand model containing the new values.

    Raises
    ------
    pydantic.ValidationError
        If the updated model is invalid.

    Returns
    -------
    AppCommand
        A new AppCommand model with the updated fields.
    """

    data = model.model_dump()
    update_data = update_model.model_dump()

    def deep_update(data: dict[str, Any], update: dict[str, Any]) -> None:
        for k in set(update).intersection(data):
            if isinstance(data[k], dict):
                deep_update(data[k], update[k])
            else:
                data[k] = update[k]

    deep_update(data, update_data)

    # return AppCommand.model_copy(update=data1)
    return AppCommand.model_validate(data)  # NOTE: avoid pydantic serializer warnings


async def save_yaml(data: dict[str, Any], file: Path) -> None:
    async with await file.open('w', encoding='utf-8') as f:
        yaml_text = yaml.dump(data, indent=4, allow_unicode=True, sort_keys=False)
        await f.write(yaml_text)


async def read_yaml(file: Path) -> Any:
    async with await file.open('r', encoding='utf-8') as f:
        yaml_text = await f.read()
        return yaml.safe_load(yaml_text)


# NOTE: or aiofiles?


class Translator(_Translator):
    if TYPE_CHECKING:
        __latest_command: Command[Any, ..., Any] | Group | ContextMenu
        __latest_parameter: Parameter

    def __init__(
        self,
        bot: LatteBot,
        locales: tuple[Locale, ...] | None = None,
        default_locale: Locale = Locale.american_english,
    ) -> None:
        super().__init__()
        self.bot = bot
        if not locales:
            log.warning('no supported locales provided')
        self.default_locale = default_locale
        self._locales = {default_locale, *locales} if locales else {default_locale}
        self._localization: dict[str, dict[str, Any]] = {}  # TODO: defaultdict?

    @property
    def locales(self) -> list[Locale]:
        return list(self._locales)

    async def load(self) -> None:
        log.info('loaded')

    async def unload(self) -> None:
        log.info('unloaded')

    async def translate(self, string: locale_str, locale: Locale, context: TranslationContextTypes) -> str | None:
        if locale == self.default_locale:
            return None

        if locale not in self.locales:
            return None

        tcl = context.location

        if tcl != TCL.other:
            # TODO: handle other types
            return None

        keys = self._get_localization_keys(tcl, context.data)

        if not keys:
            log.warning(
                'no keys found for: %s locale: %s tcl: %s type: %s',
                string.message,
                locale.value,
                context.location.name,
                type(context.data).__qualname__,
            )
            return None

        locale_localization = self._localization.get(locale.value)

        if not locale_localization:
            return None

        locale_string = self.get_string_by_keys(locale_localization, keys)

        if locale_string is None:
            log.warning(
                'not found: %s locale: %s tcl: %s type: %s',
                string.message,
                locale.value,
                context.location.name,
                type(context.data).__qualname__,
            )

        return locale_string

    def get_string_by_keys(self, localization_data: dict[str, Any], keys: list[str]) -> str | None:
        value: str | dict[str, Any] | None = None
        with contextlib.suppress(KeyError, TypeError):
            value = reduce(lambda d, k: d[k], keys, localization_data)

        if value is None:
            log.error('failed to get value by keys: %s', keys)
            return None

        if not isinstance(value, str):
            log.error('value is not a string: %s get by keys: %s', value, keys)
            return None

        return value

    def _get_localization_keys(self, tcl: TCL, translatable: Translatable) -> list[str]:
        keys = []

        if tcl in {TCL.command_name, TCL.group_name} and isinstance(translatable, Command | Group | ContextMenu):
            keys.extend([translatable.qualified_name, 'name'])
            self.__latest_command = translatable

        elif tcl in {TCL.command_description, TCL.group_description} and isinstance(translatable, Command | Group):
            keys.extend([translatable.qualified_name, 'description'])

        elif tcl == TCL.parameter_name and isinstance(translatable, Parameter):
            keys.extend([
                translatable.command.qualified_name,
                'options',
                translatable.name,
                'display_name',
            ])
            self.__latest_parameter = translatable

        elif tcl == TCL.parameter_description and isinstance(translatable, Parameter):
            keys.extend([
                translatable.command.qualified_name,
                'options',
                translatable.name,
                'description',
            ])

        elif (
            tcl == TCL.choice_name
            and isinstance(translatable, Choice)
            and hasattr(self, '__latest_command')
            and hasattr(self, '__latest_parameter')
        ):
            # validate latest command and parameter

            # if not isinstance(self.__latest_command, Command | Group | ContextMenu):
            #     raise TypeError('latest command is not a discord.app_commands.Command')

            # if not isinstance(self.__latest_parameter, Parameter):
            #     raise TypeError('latest parameter is not a discord.app_commands.Parameter')

            # NOTE: Actually, we don't need to validate it because it's an instance of Command and Parameter already
            # Just want to check it to make sure that it's an instance of Command and Parameter

            keys.extend([
                self.__latest_command.qualified_name,
                'options',
                self.__latest_parameter.name,
                'choices',
                str(translatable.value),
            ])

        return keys

    async def load_translations(self) -> None:
        bot_cogs = self.bot.cogs.values()
        for cog in bot_cogs:
            locales_path = await self._get_locales_path(cog)
            if locales_path is None:
                continue

            for locale in self.locales:
                await self._process_locale(cog, locale, locales_path)
        log.info('loaded translations')

    async def _get_locales_path(self, cog: Cog) -> Path | None:
        cog_module = inspect.getmodule(cog)
        if cog_module is None:
            log.warning('No module found for cog %s', cog.qualified_name)
            return None

        cog_file_path = inspect.getfile(cog_module)
        cog_directory = Path(cog_file_path).parent
        locales_path = cog_directory / 'locales'

        if not await locales_path.exists():
            return None
        return locales_path

    async def _process_locale(self, cog: Cog, locale: Locale, locales_path: Path) -> None:
        is_default_locale = locale == self.default_locale
        locale_filename = 'default' if is_default_locale else locale.value
        locale_file = locales_path / f'{locale_filename}.yaml'

        # await self._ensure_locale_file(locale_file)
        if not await locale_file.exists():
            if await (invalid_file := locale_file.with_suffix('.yml')).exists():
                # TODO: rename extension to .yaml
                # invalid_file.rename(locale_file)
                raise FileExistsError(f'Please use .yaml instead of .yml for locale files: {invalid_file.as_posix()!r}')
            await locale_file.touch()

        locale_data: dict[str, Any] = await read_yaml(locale_file)

        if is_default_locale or locale_data is None:
            commands_data = await self._get_app_commands_data(cog)
            self._update_localization(locale, commands_data)
            await save_yaml(commands_data, locale_file)
        else:
            updated_commands_data = await self._update_app_commands_data(cog, locale_data)
            self._update_localization(locale, updated_commands_data)
            await save_yaml(updated_commands_data, locale_file)

    async def _get_app_commands_data(self, cog: Cog, *, exclude_none: bool = True) -> dict[str, dict[str, Any]]:
        return {
            command.qualified_name: get_app_command_model(command).model_dump(exclude_none=exclude_none)
            for command in cog.walk_app_commands()
        }

    async def _update_app_commands_data(self, cog: Cog, locale_data: dict[str, Any]) -> dict[str, Any]:
        updated_commands_data = {}
        for command in cog.walk_app_commands():
            command_name = command.qualified_name
            command_model = get_app_command_model(command)

            if command_name in locale_data:
                existing_command_data = AppCommand.model_validate(locale_data[command_name])
                updated_command_model = update_app_command_model(
                    command_model,
                    existing_command_data,
                )
                updated_commands_data[command_name] = updated_command_model.model_dump(exclude_none=True)
            else:
                updated_commands_data[command_name] = command_model.model_dump(exclude_none=True)
        return updated_commands_data

    def _update_localization(self, locale: Locale, commands_data: dict[str, Any]) -> None:
        if locale.value not in self._localization:
            self._localization[locale.value] = commands_data
        else:
            self._localization[locale.value].update(commands_data)

    def clear(self) -> None:
        self._localization.clear()
        with contextlib.suppress(AttributeError):
            del self.__latest_command
            del self.__latest_parameter
