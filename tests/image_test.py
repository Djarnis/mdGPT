import pytest
from pathlib import Path
from mdgpt import cli


@pytest.fixture
def cli_args():
    return [
        'image',
        'tests/prompts/prompts',
        '--file',
        'index.md',
    ]


def test_create_image(cli_args, monkeypatch):
    monkeypatch.setattr('sys.argv', ['prog_name'] + cli_args)
    cli()
