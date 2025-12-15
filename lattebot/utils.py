from __future__ import annotations

import json
from functools import partial
from typing import Any

import yaml
from anyio import Path

try:
    import msgspec
except ImportError:  # pragma: no cover
    msgspec = None  # type: ignore[assignment]

# JSON utils
_from_json = json.loads if msgspec is None else msgspec.json.decode
_to_json = json.dumps if msgspec is None else msgspec.json.encode
# _json_format = None if msgspec is None else msgspec.json.format

# YAML utils
_from_yaml = yaml.safe_load if msgspec is None else msgspec.yaml.decode

# NOTE: encoding='utf-8' is passed to yaml.safe_dump to ensure it returns bytes,
# making it consistent with msgspec.yaml.encode which also returns bytes.
# Without encoding, yaml.safe_dump would return a string.
_to_yaml = partial(yaml.safe_dump, encoding='utf-8') if msgspec is None else msgspec.yaml.encode


# NOTE: or aiofiles?


async def save_yaml(  # noqa: PLR0913
    file: Path | str,
    data: dict[str, Any],
    *,
    overwrite: bool = False,
    indent: int = 4,
    allow_unicode: bool = True,
    sort_keys: bool = False,
    **kwargs: Any,
) -> None:
    """
    Save a dictionary to a YAML file.

    Parameters
    ----------
    data : dict[str, Any]
        The dictionary data to save.
    file : anyio.Path
        The file path where the YAML content will be written.
    overwrite : bool
        Whether to overwrite the file if it already exists. Default is False.
    indent : int
        The number of spaces to use for indentation. Default is 4.
    allow_unicode : bool
        Whether to allow Unicode characters in the output. Default is True.
    sort_keys : bool
        Whether to sort the keys in the output. Default is False.
    **kwargs : Any
        Additional keyword arguments to pass to yaml.dump().

    Raises
    ------
    FileExistsError
        If the file already exists and overwrite is False.
    """
    if isinstance(file, str):
        file = Path(file)

    if not overwrite and await file.exists():
        raise FileExistsError(f'File {file} already exists.')

    async with await file.open('w', encoding='utf-8') as f:
        yaml_text = yaml.dump(
            data,
            indent=indent,
            allow_unicode=allow_unicode,
            sort_keys=sort_keys,
            **kwargs,
        )
        await f.write(yaml_text)


async def read_yaml(file: Path | str) -> Any:
    """
    Read a YAML file and returns its content.

    Parameters
    ----------
    file : anyio.Path
        The file path to read the YAML content from.

    Returns
    -------
    Any
        The content of the YAML file.
    """
    if isinstance(file, str):
        file = Path(file)

    async with await file.open('r', encoding='utf-8',) as f:
        yaml_text = await f.read()
        return _from_yaml(yaml_text)


async def read_json(file: Path | str) -> Any:
    """
    Read a JSON file and returns its content.

    Parameters
    ----------
    file : anyio.Path
        The file path to read the JSON content from.

    Returns
    -------
    Any
        The content of the JSON file.
    """
    if isinstance(file, str):
        file = Path(file)

    async with await file.open('r', encoding='utf-8') as f:
        json_text = await f.read()
        return _from_json(json_text)


async def save_json(
    file: Path | str,
    data: dict[str, Any],
    *,
    overwrite: bool = False,
) -> None:
    """
    Save a dictionary to a JSON file.

    Parameters
    ----------
    data : dict[str, Any]
        The dictionary data to save.
    file : anyio.Path
        The file path where the JSON content will be written.
    overwrite : bool
        Whether to overwrite the file if it already exists. Default is False.

    Raises
    ------
    FileExistsError
        If the file already exists and overwrite is False.
    """
    if isinstance(file, str):
        file = Path(file)

    if not overwrite and await file.exists():
        raise FileExistsError(f'File {file} already exists.')

    await file.write_bytes(_to_json(data))
