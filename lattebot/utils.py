from __future__ import annotations

import json
import tomllib
from functools import partial
from typing import Any, Literal, overload

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
) -> Any: ...


@overload
async def read_json(
    file_path: Path | str,
    *,
    raise_on_error: Literal[False] = False,
) -> Any | None: ...


async def read_json(
    file_path: Path | str,
    *,
    raise_on_error: bool = False,
) -> Any | None:
    """Read and parse a JSON file.

    Args:
        file_path: Path to the JSON file to read.
        raise_on_error: If True, raise exceptions for any errors (file not found,
            invalid JSON). If False, return None on errors. Default is False.

    Returns
    -------
        The parsed JSON content (dict, list, or other JSON types).
        Returns None if an error occurs and raise_on_error is False.

    Raises
    ------
        FileNotFoundError: If raise_on_error=True and the file does not exist.
        FileFormatError: If raise_on_error=True and the file contains invalid JSON.

    Examples
    --------
    ```python
    # Return None on errors
    data = await read_json("config.json")
    if data is not None:
        print(data)

    # Raise exceptions on errors
    data = await read_json("config.json", raise_on_error=True)
    print(data)  # Guaranteed to be valid JSON, not None
    ```
    """
    if isinstance(file_path, str):
        file_path = Path(file_path)

    if not await file_path.exists():
        if raise_on_error:
            raise FileNotFoundError(f'File {file_path} does not exist.')
        return None

    json_text = await file_path.read_text(encoding='utf-8')

    try:
        return _from_json(json_text)
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
    """Save data to a JSON file atomically.

    Uses a temporary file and atomic rename to ensure the file is either fully
    written or not modified at all, preventing corruption from partial writes.

    Args:
        file_path: Path where the JSON file will be written.
        data: Data to serialize to JSON (must be JSON-serializable).
        indent: Number of spaces for indentation. None for compact output.
            Default is None.
        overwrite: If False, raise FileExistsError if file already exists.
            If True, overwrite existing file. Default is False.

    Raises
    ------
        FileExistsError: If the file exists and overwrite is False.
        TypeError: If data is not JSON-serializable.

    Examples
    --------
    ```python
    # Save with pretty printing
    await save_json("config.json", {"key": "value"}, indent=2)

    # Save compact JSON
    await save_json("data.json", [1, 2, 3])

    # Overwrite existing file
    await save_json("config.json", {"new": "data"}, overwrite=True)
    ```
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
    except Exception:  # pragma: no cover
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
) -> Any: ...


@overload
async def read_yaml(
    file_path: Path | str,
    *,
    raise_on_error: Literal[False] = False,
) -> Any | None: ...


async def read_yaml(
    file_path: Path | str,
    *,
    raise_on_error: bool = False,
) -> Any | None:
    """Read and parse a YAML file.

    Args:
        file_path: Path to the YAML file to read.
        raise_on_error: If True, raise exceptions for any errors (file not found,
            invalid YAML). If False, return None on errors. Default is False.

    Returns
    -------
        The parsed YAML content (dict, list, or other YAML types).
        Returns None if an error occurs and raise_on_error is False.

    Raises
    ------
        FileNotFoundError: If raise_on_error=True and the file does not exist.
        FileFormatError: If raise_on_error=True and the file contains invalid YAML.

    Examples
    --------
    ```python
    # Return None on errors
    config = await read_yaml("settings.yaml")
    if config is not None:
        print(config)

    # Raise exceptions on errors
    config = await read_yaml("settings.yaml", raise_on_error=True)
    print(config)  # Guaranteed to be valid YAML, not None
    ```
    """
    if isinstance(file_path, str):
        file_path = Path(file_path)

    if not await file_path.exists():
        if raise_on_error:
            raise FileNotFoundError(f'File {file_path} does not exist.')
        return None

    yaml_text = await file_path.read_text(encoding='utf-8')

    try:
        return _from_yaml(yaml_text)
    except YamlDecodeError as e:
        if raise_on_error:
            raise FileFormatError(f'Invalid YAML in file {file_path}: {e}') from e
        return None


async def save_yaml(
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
    """Save data to a YAML file atomically.

    Uses a temporary file and atomic rename to ensure the file is either fully
    written or not modified at all, preventing corruption from partial writes.

    Args:
        file_path: Path where the YAML file will be written.
        data: Data to serialize to YAML (must be YAML-serializable).
        overwrite: If False, raise FileExistsError if file already exists.
            If True, overwrite existing file. Default is False.
        indent: Number of spaces for indentation. Default is 4.
        allow_unicode: If True, allow Unicode characters in output.
            If False, encode as escape sequences. Default is True.
        sort_keys: If True, sort dictionary keys in output. Default is False.
        encoding: Text encoding for the output file. Default is 'utf-8'.
        **kwargs: Additional keyword arguments passed to yaml.dump().

    Raises
    ------
        FileExistsError: If the file exists and overwrite is False.
        yaml.YAMLError: If data cannot be serialized to YAML.

    Examples
    --------
    ```python
    # Save with custom formatting
    await save_yaml("config.yaml", {"key": "value"}, indent=2)

    # Save with sorted keys
    await save_yaml("data.yaml", {"z": 1, "a": 2}, sort_keys=True)

    # Overwrite existing file
    await save_yaml("config.yaml", {"new": "data"}, overwrite=True)
    ```

    Note:
        This function uses yaml.safe_dump instead of msgspec.yaml.encode
        to support custom formatting options (indent, sort_keys, etc.).
        msgspec.yaml.encode does not support these parameters.
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

    # use yaml.safe_dump to support formatting parameters
    # msgspec.yaml.encode does not support indent, sort_keys, etc.
    yaml_bytes = yaml.safe_dump(
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
    except Exception:  # pragma: no cover
        # remove temp file if an error occurs
        await tmp_path.unlink(missing_ok=True)
        raise


# TOML utils

TomlDecodeError = tomllib.TOMLDecodeError


@overload
async def read_toml(
    file_path: Path | str,
    *,
    raise_on_error: Literal[True],
) -> dict[str, Any]: ...


@overload
async def read_toml(
    file_path: Path | str,
    *,
    raise_on_error: Literal[False] = False,
) -> dict[str, Any] | None: ...


async def read_toml(
    file_path: Path | str,
    *,
    raise_on_error: bool = False,
) -> dict[str, Any] | None:
    """Read and parse a TOML file.

    Args:
        file_path: Path to the TOML file to read.
        raise_on_error: If True, raise exceptions for any errors (file not found,
            invalid TOML). If False, return None on errors. Default is False.

    Returns
    -------
        The parsed TOML content as a dictionary.
        Returns None if an error occurs and raise_on_error is False.

    Raises
    ------
        FileNotFoundError: If raise_on_error=True and the file does not exist.
        FileFormatError: If raise_on_error=True and the file contains invalid TOML.

    Examples
    --------
    ```python
    # Return None on errors
    config = await read_toml("pyproject.toml")
    if config is not None:
        print(config)
    # Raise exceptions on errors
    config = await read_toml("pyproject.toml", raise_on_error=True)
    print(config)  # Guaranteed to be valid TOML, not None
    ```
    """
    if isinstance(file_path, str):
        file_path = Path(file_path)

    if not await file_path.exists():
        if raise_on_error:
            raise FileNotFoundError(f'File {file_path} does not exist.')
        return None

    toml_text = await file_path.read_text(encoding='utf-8')

    try:
        return tomllib.loads(toml_text)
    except TomlDecodeError as e:
        if raise_on_error:
            raise FileFormatError(f'Invalid TOML in file {file_path}: {e}') from e
        return None
