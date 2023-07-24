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
    monkeypatch.setattr('sys.argv', ["prog_name"] + cli_args)
    cli()

    indexfile = Path('./example-test/en/index.md')
    assert indexfile.exists()
