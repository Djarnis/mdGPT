import pytest
from mdgpt import cli


@pytest.fixture
def cli_args():
    return [
        'debug',
        'tests/prompts/prompts',
    ]


def test_debug(cli_args, monkeypatch):
    monkeypatch.setattr('sys.argv', ['prog_name'] + cli_args)

    cli()
