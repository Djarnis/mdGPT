import pytest
from pathlib import Path
from mdgpt import build


@pytest.fixture
def cli_args():
    return [
        "-d", "./example-test",
        "-p", "./tests/prompts",
        "-l", "en",
    ]


def test_build(cli_args, monkeypatch):
    monkeypatch.setattr('sys.argv', ["prog_name"] + cli_args)
    build()

    indexfile = Path('./example-test/en/index.md')
    assert indexfile.exists()
