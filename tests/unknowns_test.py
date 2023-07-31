import os
import pytest
from pathlib import Path
from mdgpt import cli



@pytest.fixture
def cli_args_test_unknown_action():
    return [
        'unknown_action',
        'tests/prompts/prompts',
    ]


def test_unknown_action(cli_args_test_unknown_action, monkeypatch):
    monkeypatch.setattr('sys.argv', ['prog_name'] + cli_args_test_unknown_action)
    # cli()

    with pytest.raises(SystemExit) as pytest_wrapped_e:
        cli()

    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code == 1


@pytest.fixture
def cli_args_test_wront_openai_key():
    return [
        'translate',
        'tests/prompts/prompts',
        '--target',
        'za'
    ]


def test_wrong_openai_key(cli_args_test_wront_openai_key, monkeypatch):
    monkeypatch.setattr('sys.argv', ['prog_name'] + cli_args_test_wront_openai_key)

    envs = {'OPENAI_API_KEY': 'wrong_key'}
    monkeypatch.setattr(os, 'environ', envs)

    with pytest.raises(SystemExit) as pytest_wrapped_e:
        cli()

    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code == 1

    print('OPENAI_API_KEY', os.getenv('OPENAI_API_KEY'))
