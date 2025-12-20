import pytest

from lattebot.core.translator import (
    AppCommandModel,
    _update_app_command_model,  # noqa: PLC2701
)


@pytest.mark.anyio
def test_update_app_command_data() -> None:
    app_command = AppCommandModel.model_validate({
        'name': 'a',
        'description': 'a',
        'options': {
            'param_1': {
                'display_name': 'p1',
                'description': 'p1d',
                'choices': {'1': '1', '2': '2', '3': '3'},
            },
            'param_2': {
                'display_name': 'p2',
                'description': 'p2d',
            },
        },
    })

    app_command_update = AppCommandModel.model_validate({
        'name': 'b',
        'description': 'b',
        'options': {
            'param_1': {
                'display_name': 'p1x',
                'description': 'p1dx',
                'choices': {'1': '1x', '3': '3x', '4': '4'},
            },
            'param_2': {
                'display_name': 'p2x',
                'description': 'p2dx',
                'choices': None,
            },
            'param_3': {
                'display_name': 'p3',
                'description': 'p3d',
            },
        },
    })

    updated_app_command = _update_app_command_model(app_command, app_command_update)
    updated_app_command_data = updated_app_command.model_dump()

    assert updated_app_command_data == {
        'name': 'b',
        'description': 'b',
        'options': {
            'param_1': {
                'display_name': 'p1x',
                'description': 'p1dx',
                'choices': {'1': '1x', '2': '2', '3': '3x'},
            },
            'param_2': {
                'display_name': 'p2x',
                'description': 'p2dx',
                'choices': None,
            },
        },
    }
