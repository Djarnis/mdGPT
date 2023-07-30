import pytest
from pathlib import Path
from mdgpt import cli


@pytest.fixture
def cli_args():
    return [
        'build',
        'tests/prompts',
    ]


def test_build(cli_args, monkeypatch):
    monkeypatch.setattr('sys.argv', ['prog_name'] + cli_args)
    cli()

    indexfile = Path('./example-test/en/index.md')
    assert indexfile.exists()


@pytest.fixture
def cli_args_file():
    return [
        'build',
        'tests/prompts',
        '--file',
        'index.md',
    ]


def test_build_file(cli_args_file, monkeypatch):
    target_path = './example-test/en/index.md'
    file_path = Path(target_path)
    if file_path.exists():
        file_path.unlink()

    monkeypatch.setattr('sys.argv', ['prog_name'] + cli_args_file)
    cli()

    indexfile = Path(target_path)
    assert indexfile.exists()
