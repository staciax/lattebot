from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from anyio import Path as AnyioPath

from lattebot.utils import read_yaml, save_yaml

if TYPE_CHECKING:
    from anyio import Path


@pytest.mark.anyio
async def test_save_yaml(tmp_path: Path) -> None:
    data = {'key': 'value'}
    file_path = AnyioPath(tmp_path / 'test.yaml')

    await save_yaml(file_path, data)

    assert await file_path.exists()
    async with await file_path.open('r', encoding='utf-8') as f:
        content = await f.read()
        assert 'key: value' in content


@pytest.mark.anyio
async def test_save_yaml_string_path(tmp_path: Path) -> None:
    data = {'key': 'value'}
    file_path = AnyioPath(tmp_path / 'test.yaml')

    await save_yaml(file_path.as_posix(), data)

    assert file_path.exists()
    async with await file_path.open('r', encoding='utf-8') as f:
        content = await f.read()
        assert 'key: value' in content


@pytest.mark.anyio
async def test_read_yaml(tmp_path: Path) -> None:
    data = {'key': 'value'}
    file_path = AnyioPath(tmp_path / 'test.yaml')

    async with await file_path.open('w', encoding='utf-8') as f:
        await f.write('key: value')

    result = await read_yaml(file_path)
    assert result == data


@pytest.mark.anyio
async def test_read_yaml_string_path(tmp_path: Path) -> None:
    data = {'key': 'value'}
    file_path = AnyioPath(tmp_path / 'test.yaml')

    async with await file_path.open('w', encoding='utf-8') as f:
        await f.write('key: value')

    result = await read_yaml(file_path.as_posix())
    assert result == data
