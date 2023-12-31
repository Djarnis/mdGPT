import pytest
from pathlib import Path
from mdgpt import cli


@pytest.fixture
def cli_args_test_build():
    return [
        'build',
        'tests/prompts/prompts',
    ]


def test_build(cli_args_test_build, monkeypatch):
    monkeypatch.setattr('sys.argv', ['prog_name'] + cli_args_test_build)

    cli()

    # Add a README.md file ...
    Path('./example-test/en/README.md').write_text('This is a README.md file')

    assert Path('./example-test/en/index.md').exists()


@pytest.fixture
def cli_args_test_build_file():
    return [
        'build',
        'tests/prompts/prompts',
        '--file',
        'index.md',
    ]


def test_build_file(cli_args_test_build_file, monkeypatch):
    target_path = Path('./example-test/en/index.md')
    target_path.unlink() if target_path.exists() else ...

    monkeypatch.setattr('sys.argv', ['prog_name'] + cli_args_test_build_file)

    cli()

    assert Path(target_path).exists()


@pytest.fixture
def cli_args_test_build_invalid_prompt():
    return [
        'build',
        'tests/prompts/prompts_no_builder',
    ]


def test_build_invalid_prompt(cli_args_test_build_invalid_prompt, monkeypatch):
    monkeypatch.setattr('sys.argv', ['prog_name'] + cli_args_test_build_invalid_prompt)

    with pytest.raises(SystemExit) as pytest_wrapped_e:
        cli()

    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code == 1


@pytest.fixture
def cli_args_test_build_invalid_lang():
    return [
        'build',
        'tests/prompts/prompts',
        '--lang',
        'chineese',
    ]


def test_build_invalid_lang(cli_args_test_build_invalid_lang, monkeypatch):
    monkeypatch.setattr('sys.argv', ['prog_name'] + cli_args_test_build_invalid_lang)

    with pytest.raises(SystemExit) as pytest_wrapped_e:
        cli()

    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code == 1


@pytest.fixture
def cli_args_test_build_invalid_lang_2():
    return [
        'build',
        'tests/prompts/prompts',
        '--lang',
        'xx',
    ]


def test_build_invalid_lang_2(cli_args_test_build_invalid_lang_2, monkeypatch):
    monkeypatch.setattr('sys.argv', ['prog_name'] + cli_args_test_build_invalid_lang_2)

    with pytest.raises(SystemExit) as pytest_wrapped_e:
        cli()

    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code == 1
