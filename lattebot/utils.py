from __future__ import annotations

from typing import Any

import yaml
from anyio import Path


async def save_yaml(data: dict[str, Any], file: Path | str) -> None:
    """
    Save a dictionary to a YAML file.

    Parameters
    ----------
    data : dict[str, Any]
        The dictionary data to save.
    file : anyio.Path
        The file path where the YAML content will be written.
    """
    if isinstance(file, str):
        file = Path(file)

    async with await file.open('w', encoding='utf-8') as f:
        yaml_text = yaml.dump(data, indent=4, allow_unicode=True, sort_keys=False)
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
    async with await file.open('r', encoding='utf-8') as f:
        yaml_text = await f.read()
        return yaml.safe_load(yaml_text)


# NOTE: or aiofiles?
