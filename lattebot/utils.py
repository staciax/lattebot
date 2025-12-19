from __future__ import annotations

import json
from functools import partial
from typing import Any, Literal, cast, overload

import yaml
from anyio import Path

try:
    import msgspec
except ImportError:  # pragma: no cover
    msgspec = None  # type: ignore[assignment,unused-ignore]


# JSON utils
_from_json = json.loads if msgspec is None else msgspec.json.decode
_to_json = json.dumps if msgspec is None else msgspec.json.encode

# YAML utils
_from_yaml = yaml.safe_load if msgspec is None else msgspec.yaml.decode

# NOTE: encoding='utf-8' is passed to yaml.safe_dump to ensure it returns bytes,
# making it consistent with msgspec.yaml.encode which also returns bytes.
# Without encoding, yaml.safe_dump would return a string.
_to_yaml = partial(yaml.safe_dump, encoding='utf-8') if msgspec is None else msgspec.yaml.encode

# NOTE: I should switch from anyio.Path to aiofiles library???


class FileFormatError(Exception):
    """Raised when file content is invalid."""


# JSON utils

JsonDecodeError = json.JSONDecodeError if msgspec is None else msgspec.DecodeError


@overload
async def read_json(
    file_path: Path | str,
    *,
    raise_on_error: Literal[True],
) -> dict[str, Any]: ...


@overload
async def read_json(
    file_path: Path | str,
    *,
    raise_on_error: Literal[False] = False,
) -> dict[str, Any] | None: ...


async def read_json(
    file_path: Path | str,
    *,
    raise_on_error: bool = False,
) -> dict[str, Any] | None:
    """Read a JSON file and returns its content.

    Args:
        file_path: The file path to read the JSON content from.
        raise_on_error: If True, raise exceptions on any errors. Default is False.

    Returns
    -------
        The content of the JSON file, or None if any error occurs (when raise_on_error=False).

    Raises
    ------
        FileNotFoundError: If raise_on_error=True and the file does not exist.
        FileFormatError: If raise_on_error=True and decoding fails.
    """
    if isinstance(file_path, str):
        file_path = Path(file_path)

    if not await file_path.exists():
        if raise_on_error:
            raise FileNotFoundError(f'File {file_path} does not exist.')
        return None

    json_text = await file_path.read_text(encoding='utf-8')
    try:
        return cast('dict[str, Any]', _from_json(json_text))
    except JsonDecodeError as e:
        if raise_on_error:
            raise FileFormatError(f'Invalid JSON in file {file_path}: {e}') from e
        return None


async def save_json(
    file_path: Path | str,
    data: dict[str, Any],
    *,
    indent: int | None = None,
    overwrite: bool = False,
) -> None:
    """Save a dictionary to a JSON file.

    Args:
        file_path: The file path where the JSON content will be written.
        data: The dictionary data to save.
        indent: Number of spaces for indentation (None for compact).
        overwrite: Whether to overwrite the file if it already exists. Default is False.

    Raises
    ------
        FileExistsError: If the file already exists and overwrite is False.
    """
    if isinstance(file_path, str):
        file_path = Path(file_path)

    if not overwrite and await file_path.exists():
        raise FileExistsError(f'File {file_path} already exists.')

    # ensure parent directories exist
    await file_path.parent.mkdir(parents=True, exist_ok=True)

    tmp_path = file_path.with_suffix(file_path.suffix + '.tmp')

    # encode with indent support for both msgspec and json
    if msgspec is not None:
        json_data = msgspec.json.encode(data)
        if indent:
            json_data = msgspec.json.format(json_data, indent=indent)
    else:
        json_data = json.dumps(data, indent=indent).encode('utf-8')

    try:
        await tmp_path.write_bytes(json_data)
        await tmp_path.replace(file_path)
    except Exception:
        # remove temp file if an error occurs
        await tmp_path.unlink(missing_ok=True)
        raise


# YAML utils

YamlDecodeError = yaml.YAMLError if msgspec is None else msgspec.DecodeError


@overload
async def read_yaml(
    file_path: Path | str,
    *,
    raise_on_error: Literal[True],
) -> dict[str, Any]: ...


@overload
async def read_yaml(
    file_path: Path | str,
    *,
    raise_on_error: Literal[False] = False,
) -> dict[str, Any] | None: ...


async def read_yaml(
    file_path: Path | str,
    *,
    raise_on_error: bool = False,
) -> dict[str, Any] | None:
    """Read a YAML file and returns its content.

    Args:
        file_path: The file path to read the YAML content from.
        raise_on_error: If True, raise exceptions on any errors. Default is False.

    Returns
    -------
        The content of the YAML file, or None if any error occurs (when raise_on_error=False).

    Raises
    ------
        FileNotFoundError: If raise_on_error=True and the file does not exist.
        FileFormatError: If raise_on_error=True and decoding fails.
    """
    if isinstance(file_path, str):
        file_path = Path(file_path)

    if not await file_path.exists():
        if raise_on_error:
            raise FileNotFoundError(f'File {file_path} does not exist.')
        return None

    yaml_text = await file_path.read_text(encoding='utf-8')
    try:
        return cast('dict[str, Any]', _from_yaml(yaml_text))
    except YamlDecodeError as e:
        if raise_on_error:
            raise FileFormatError(f'Invalid YAML in file {file_path}: {e}') from e
        return None


async def save_yaml(  # noqa: PLR0913
    file_path: Path | str,
    data: dict[str, Any],
    *,
    overwrite: bool = False,
    indent: int = 4,
    allow_unicode: bool = True,
    sort_keys: bool = False,
    encoding: str = 'utf-8',
    **kwargs: Any,
) -> None:
    """Save a dictionary to a YAML file.

    Args:
        file_path: The file path where the YAML content will be written.
        data: The dictionary data to save.
        overwrite: Whether to overwrite the file if it already exists. Default is False.
        indent: The number of spaces to use for indentation. Default is 4.
        allow_unicode: Whether to allow Unicode characters in the output. Default is True.
        sort_keys: Whether to sort the keys in the output. Default is False.
        encoding: The encoding to use. Default is 'utf-8'.
        **kwargs: Additional keyword arguments to pass to yaml.dump().

    Raises
    ------
        FileExistsError: If the file already exists and overwrite is False.
    """
    if isinstance(file_path, str):
        file_path = Path(file_path)

    if not overwrite and await file_path.exists():
        raise FileExistsError(f'File {file_path} already exists.')

    # ensure parent directories exist
    await file_path.parent.mkdir(parents=True, exist_ok=True)

    tmp_path = file_path.with_suffix(file_path.suffix + '.tmp')

    # if msgspec is not None:
    #     yaml_bytes = msgspec.yaml.encode(data)
    # else:
    yaml_bytes = yaml.dump(
        data,
        indent=indent,
        allow_unicode=allow_unicode,
        sort_keys=sort_keys,
        encoding=encoding,
        **kwargs,
    )

    try:
        await tmp_path.write_bytes(yaml_bytes)
        await tmp_path.replace(file_path)
    except Exception:
        # remove temp file if an error occurs
        await tmp_path.unlink(missing_ok=True)
        raise
