import pytest
from pathlib import Path

from mdgpt import engines


@pytest.fixture
def cli_args():
    return []


def test_list_engines(cli_args, monkeypatch):
    monkeypatch.setattr('sys.argv', ["prog_name"] + cli_args)
    engines()

    # indexfile = Path('./example-test/da/index.md')
    # assert indexfile.exists()
