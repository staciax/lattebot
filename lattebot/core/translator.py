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


def model_deep_update[M: BaseModel](model1: M, model2: M) -> M:
    """
    Deep update model1 with model2

    Parameters
    ----------
    model1 : pydantic.BaseModel
        The model to update
    model2 : pydantic.BaseModel
        The model to update with

    Raises
    ------
    pydantic.ValidationError
        If the updated model is invalid

    Returns
    -------
    pydantic.BaseModel
        The updated model
    """

    data1 = model1.model_dump()
    data2 = model2.model_dump()

    def deep_update(data: dict[str, Any], update: dict[str, Any]) -> None:
        for k in set(update).intersection(data):
            if isinstance(data[k], dict):
                deep_update(data[k], update[k])
            else:
                data[k] = update[k]

    deep_update(data1, data2)

    return type(model1).model_validate(data1)
    # return model1.model_copy(update=data1)


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
    def __init__(
        self,
        bot: LatteBot,
        locales: tuple[Locale, ...] | None = None,
    ) -> None:
        super().__init__()
        self.bot = bot
        if not locales:
            log.warning('no supported locales provided')
        self._locales = locales or ()
        self._localization: dict[str, dict[str, Any]] = {}  # TODO: defaultdict?
        # self.__latest_command: Command | Group | ContextMenu  # type: ignore[type-arg]
        # self.__latest_parameter: Parameter

    @property
    def locales(self) -> list[Locale]:
        return list(self._locales)

    async def load(self) -> None:
        log.info('loaded')

    async def unload(self) -> None:
        log.info('unloaded')

    async def translate(self, string: locale_str, locale: Locale, context: TranslationContextTypes) -> str | None:
        if locale == Locale.american_english:
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

        elif tcl == TCL.choice_name and (
            getattr(self, '__latest_command', None)
            and getattr(self, '__latest_parameter', None)
            and isinstance(translatable, Choice)
        ):
            keys.extend([
                self.__latest_command.qualified_name,
                'options',
                self.__latest_parameter.name,
                'choices',
                str(translatable.value),
            ])

        return keys

    async def load_translations(self) -> None:  # noqa: PLR0912
        cogs = self.bot.cogs.values()
        for cog in cogs:
            module = inspect.getmodule(cog)

            if module is None:
                raise ImportError('No module found for cog')

            cog_file = inspect.getfile(module)
            # print('cog_file', cog_file)
            cog_path = Path(cog_file).parent
            locales_path = cog_path / 'locales'

            if not await locales_path.exists():
                # print(cog.qualified_name, locales_path, cog_path)
                log.warning(f'No locales folder found for cog {cog.qualified_name}')  # noqa: G004
                continue

            for locale in self.locales:
                is_fallback = locale == Locale.american_english
                filename = 'fallback' if is_fallback else locale.value
                locale_file_path = locales_path / f'{filename}.yaml'

                # print(locale_file.as_uri())

                if not await locale_file_path.exists():
                    if (invalid_file := locale_file_path.with_suffix('.yml')).exists():
                        # TODO: rename extension to .yaml
                        # invalid_file.rename(locale_file)
                        raise FileExistsError(
                            f'Please use .yaml instead of .yml for locale files: {invalid_file.as_uri()!r}'
                        )
                    await locale_file_path.touch()

                data: dict[str, Any] = await read_yaml(locale_file_path)

                if is_fallback or data is None:
                    commands_data = {
                        app_command.qualified_name: get_app_command_model(app_command).model_dump(exclude_none=True)
                        for app_command in cog.walk_app_commands()
                    }
                    await save_yaml(commands_data, locale_file_path)

                    if locale.value not in self._localization:
                        self._localization[locale.value] = commands_data
                    else:
                        self._localization[locale.value].update(commands_data)
                else:
                    commands_data_overwrite = {}
                    for app_command in cog.walk_app_commands():
                        key = app_command.qualified_name
                        value = get_app_command_model(app_command)

                        if key in data:
                            app_command_model_data = AppCommand.model_validate(data[key])
                            update = model_deep_update(value, app_command_model_data)
                            commands_data_overwrite[key] = update.model_dump(exclude_none=True)
                        else:
                            commands_data_overwrite[key] = value.model_dump(exclude_none=True)

                    if locale.value not in self._localization:
                        self._localization[locale.value] = commands_data_overwrite
                    else:
                        self._localization[locale.value].update(commands_data_overwrite)

                    await save_yaml(commands_data_overwrite, locale_file_path)

    def clear(self) -> None:
        self._localization.clear()
        with contextlib.suppress(AttributeError):
            del self.__latest_command
            del self.__latest_parameter
