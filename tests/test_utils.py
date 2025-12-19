from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from anyio import Path as AnyioPath

from lattebot.utils import _to_json, _to_yaml, read_json, read_yaml, save_json, save_yaml  # noqa: PLC2701

if TYPE_CHECKING:
    from anyio import Path


@pytest.fixture(
    params=[
        pytest.param({'key': 'value'}, id='simple'),
        pytest.param({'nested': {'key': 'value'}}, id='nested'),
        pytest.param({'list': [1, 2, 3]}, id='list'),
        pytest.param({'mixed': {'list': [1, 2], 'string': 'test'}}, id='mixed'),
        pytest.param({'boolean': True, 'null': None}, id='bool-null'),
        pytest.param({'numbers': {'int': 42, 'float': 14.0000001}}, id='numbers'),
        pytest.param({'unicode': 'สวัสดีจ้า'}, id='unicode'),
        pytest.param({'empty': {'dict': {}, 'list': []}}, id='empty'),
    ]
)
def test_data(request: pytest.FixtureRequest) -> dict[str, Any]:
    return request.param  # type: ignore[no-any-return]


# YAML Tests


@pytest.mark.anyio
@pytest.mark.parametrize('path_as_string', [True, False])
async def test_save_yaml(
    tmp_path: Path,
    test_data: dict[str, Any],
    path_as_string: bool,
) -> None:
    output_file = AnyioPath(tmp_path / 'test.yaml')

    path_input: str | AnyioPath = output_file.as_posix() if path_as_string else output_file
    await save_yaml(path_input, test_data)

    assert await output_file.exists()
    saved_content = await output_file.read_bytes()
    assert len(saved_content) > 0


@pytest.mark.anyio
@pytest.mark.parametrize('path_as_string', [True, False])
async def test_read_yaml(
    tmp_path: Path,
    test_data: dict[str, Any],
    path_as_string: bool,
) -> None:
    input_file = AnyioPath(tmp_path / 'test.yaml')

    yaml_content = _to_yaml(test_data)
    await input_file.write_bytes(yaml_content)

    path_input: str | AnyioPath = input_file.as_posix() if path_as_string else input_file
    loaded_data = await read_yaml(path_input)

    assert loaded_data == test_data


@pytest.mark.anyio
@pytest.mark.parametrize(
    ('initial_data', 'new_data', 'overwrite', 'should_raise'),
    [
        pytest.param({'key': 'initial_value'}, {'key': 'new_value'}, False, True, id='no-overwrite-raises'),
        pytest.param({'key': 'initial_value'}, {'key': 'new_value'}, True, False, id='with-overwrite-succeeds'),
    ],
)
async def test_save_yaml_overwrite_behavior(
    tmp_path: Path,
    initial_data: dict[str, Any],
    new_data: dict[str, Any],
    overwrite: bool,
    should_raise: bool,
) -> None:
    output_file = AnyioPath(tmp_path / 'test.yaml')
    path_input: AnyioPath = output_file

    await save_yaml(path_input, initial_data)
    assert await output_file.exists()

    loaded_data = await read_yaml(path_input)
    assert loaded_data == initial_data

    if should_raise:
        with pytest.raises(FileExistsError, match=r'File .* already exists\.'):
            await save_yaml(path_input, new_data, overwrite=overwrite)

        loaded_data = await read_yaml(path_input)
        assert loaded_data == initial_data
    else:
        await save_yaml(path_input, new_data, overwrite=overwrite)

        loaded_data = await read_yaml(path_input)
        assert loaded_data == new_data
        assert loaded_data != initial_data


# JSON tests


@pytest.mark.anyio
@pytest.mark.parametrize('path_as_string', [True, False])
async def test_save_json(
    tmp_path: Path,
    test_data: dict[str, Any],
    path_as_string: bool,
) -> None:
    output_file = AnyioPath(tmp_path / 'test.json')
    path_input: str | AnyioPath = output_file.as_posix() if path_as_string else output_file

    await save_json(path_input, test_data)

    assert await output_file.exists()
    saved_content = await output_file.read_bytes()
    assert len(saved_content) > 0


@pytest.mark.anyio
@pytest.mark.parametrize('path_as_string', [True, False])
async def test_read_json(
    tmp_path: Path,
    test_data: dict[str, Any],
    path_as_string: bool,
) -> None:
    input_file = AnyioPath(tmp_path / 'test.json')

    json_content = _to_json(test_data)
    await input_file.write_bytes(json_content)

    path_input: str | AnyioPath = input_file.as_posix() if path_as_string else input_file
    loaded_data = await read_json(path_input)

    assert loaded_data == test_data


@pytest.mark.anyio
@pytest.mark.parametrize(
    ('initial_data', 'new_data', 'overwrite', 'should_raise'),
    [
        pytest.param({'key': 'initial_value'}, {'key': 'new_value'}, False, True, id='no-overwrite-raises'),
        pytest.param({'key': 'initial_value'}, {'key': 'new_value'}, True, False, id='with-overwrite-succeeds'),
    ],
)
async def test_save_json_overwrite_behavior(
    tmp_path: Path,
    initial_data: dict[str, Any],
    new_data: dict[str, Any],
    overwrite: bool,
    should_raise: bool,
) -> None:
    output_file = AnyioPath(tmp_path / 'test.json')
    path_input: AnyioPath = output_file

    await save_json(path_input, initial_data)
    assert await output_file.exists()

    loaded_data = await read_json(path_input)
    assert loaded_data == initial_data

    if should_raise:
        with pytest.raises(FileExistsError, match=r'File .* already exists\.'):
            await save_json(path_input, new_data, overwrite=overwrite)

        loaded_data = await read_json(path_input)
        assert loaded_data == initial_data
    else:
        await save_json(path_input, new_data, overwrite=overwrite)

        loaded_data = await read_json(path_input)
        assert loaded_data == new_data
        assert loaded_data != initial_data
