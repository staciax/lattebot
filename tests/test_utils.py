from __future__ import annotations

import json
from typing import Any

import pytest
import yaml
from anyio import Path

from lattebot.utils import read_json, read_yaml, save_json, save_yaml


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
    output_file = Path(tmp_path / 'test.yaml')

    path_input: str | Path = output_file.as_posix() if path_as_string else output_file
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
    input_file = Path(tmp_path / 'test.yaml')

    yaml_content = yaml.safe_dump(test_data, encoding='utf-8')
    await input_file.write_bytes(yaml_content)

    path_input: str | Path = input_file.as_posix() if path_as_string else input_file
    loaded_data = await read_yaml(path_input)

    assert loaded_data == test_data


@pytest.mark.anyio
@pytest.mark.parametrize(
    ('should_raise', 'exception_type'),
    [
        pytest.param(False, None, id='no-raise-returns-none'),
        pytest.param(True, FileNotFoundError, id='raise-on-error'),
    ],
)
async def test_read_yaml_file_not_found(
    tmp_path: Path,
    should_raise: bool,
    exception_type: type[Exception] | None,
) -> None:
    input_file: Path = Path(tmp_path / 'nonexistent.yaml')

    if not should_raise:
        result = await read_yaml(input_file, raise_on_error=False)
        assert result is None
    else:
        assert exception_type is not None
        with pytest.raises(exception_type):
            await read_yaml(input_file, raise_on_error=True)


@pytest.mark.anyio
@pytest.mark.parametrize(
    ('should_raise', 'exception_type', 'invalid_content'),
    [
        pytest.param(False, None, '{ invalid: yaml: content: [', id='no-raise-returns-none'),
        pytest.param(True, Exception, '{ invalid: yaml: content: [', id='raise-on-error'),
    ],
)
async def test_read_yaml_invalid_format(
    tmp_path: Path,
    should_raise: bool,
    exception_type: type[Exception] | None,
    invalid_content: str,
) -> None:
    input_file = Path(tmp_path / 'invalid.yaml')
    await input_file.write_text(invalid_content, encoding='utf-8')

    if not should_raise:
        result = await read_yaml(input_file, raise_on_error=False)
        assert result is None
    else:
        assert exception_type is not None
        with pytest.raises(exception_type):
            await read_yaml(input_file, raise_on_error=True)


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
    output_file = Path(tmp_path / 'test.yaml')
    path_input: Path = output_file

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
    output_file = Path(tmp_path / 'test.json')
    path_input: str | Path = output_file.as_posix() if path_as_string else output_file

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
    input_file = Path(tmp_path / 'test.json')

    json_content = json.dumps(test_data)
    await input_file.write_text(json_content, encoding='utf-8')

    path_input: str | Path = input_file.as_posix() if path_as_string else input_file
    loaded_data = await read_json(path_input)

    assert loaded_data == test_data


@pytest.mark.anyio
@pytest.mark.parametrize(
    ('should_raise', 'exception_type'),
    [
        pytest.param(False, None, id='no-raise-returns-none'),
        pytest.param(True, FileNotFoundError, id='raise-on-error'),
    ],
)
async def test_read_json_file_not_found(
    tmp_path: Path,
    should_raise: bool,
    exception_type: type[Exception] | None,
) -> None:
    input_file = Path(tmp_path / 'nonexistent.json')

    if not should_raise:
        result = await read_json(input_file, raise_on_error=False)
        assert result is None
    else:
        assert exception_type is not None
        with pytest.raises(exception_type, match=r'File .* does not exist\.'):
            await read_json(input_file, raise_on_error=True)


@pytest.mark.anyio
@pytest.mark.parametrize(
    ('should_raise', 'exception_type', 'invalid_content'),
    [
        pytest.param(False, None, '{ "invalid": json content }', id='no-raise-returns-none'),
        pytest.param(True, Exception, '{ "invalid": json content }', id='raise-on-error'),
    ],
)
async def test_read_json_invalid_format(
    tmp_path: Path,
    should_raise: bool,
    exception_type: type[Exception] | None,
    invalid_content: str,
) -> None:
    input_file = Path(tmp_path / 'invalid.json')
    await input_file.write_text(invalid_content, encoding='utf-8')

    if not should_raise:
        result = await read_json(input_file, raise_on_error=False)
        assert result is None
    else:
        assert exception_type is not None
        with pytest.raises(exception_type):
            await read_json(input_file, raise_on_error=True)


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
    output_file = Path(tmp_path / 'test.json')
    path_input: Path = output_file

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


@pytest.mark.anyio
@pytest.mark.parametrize('indent', [2, 4])
async def test_save_json_with_indent(
    tmp_path: Path,
    test_data: dict[str, Any],
    indent: int,
) -> None:
    output_file = Path(tmp_path / 'test_indent.json')
    await save_json(output_file, test_data, indent=indent)

    assert await output_file.exists()
    content = await output_file.read_text()
    assert len(content) > 0

    loaded_data = await read_json(output_file)
    assert loaded_data == test_data


@pytest.mark.anyio
async def test_save_json_with_string_encoding(
    tmp_path: Path,
    test_data: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import lattebot.utils  # noqa: PLC0415

    output_file = Path(tmp_path / 'test_string.json')

    # monkeypatch to simulate msgspec not being available
    monkeypatch.setattr(lattebot.utils, 'msgspec', None)

    await save_json(output_file, test_data)

    assert await output_file.exists()
    loaded_data = await read_json(output_file)
    assert loaded_data == test_data


# TODO: add tests for read_toml
