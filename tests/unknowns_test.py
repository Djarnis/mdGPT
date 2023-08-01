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
def cli_args_test_wrong_openai_key():
    return [
        'translate',
        'tests/prompts/prompts',
        '--target',
        'za'
    ]


def test_wrong_openai_key(cli_args_test_wrong_openai_key, monkeypatch):
    monkeypatch.setattr('sys.argv', ['prog_name'] + cli_args_test_wrong_openai_key)

    envs = {'OPENAI_API_KEY': 'wrong_key'}
    monkeypatch.setattr(os, 'environ', envs)

    with pytest.raises(SystemExit) as pytest_wrapped_e:
        cli()

    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code == 1


@pytest.fixture
def cli_args_test_prompt_not_found():
    return [
        'build',
        'tests/prompts/file-not-found',
    ]


def test_prompt_not_found(cli_args_test_prompt_not_found, monkeypatch):
    monkeypatch.setattr('sys.argv', ['prog_name'] + cli_args_test_prompt_not_found)

    with pytest.raises(SystemExit) as pytest_wrapped_e:
        cli()

    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code == 1


@pytest.fixture
def cli_args_test_source_dir_params():
    return [
        'debug',
        'tests/prompts/prompts',
        '--dir',
        'example-test',
        '--source-dir',
        'en',
    ]


def test_source_dir_params(cli_args_test_source_dir_params, monkeypatch):
    monkeypatch.setattr('sys.argv', ['prog_name'] + cli_args_test_source_dir_params)

    cli()
