import pytest
from pathlib import Path

from mdgpt import translate


@pytest.fixture
def cli_args_da():
    return [
        "-d", "./example-test",
        "-p", "./tests/prompts",
        "-sl", "en",
        "-tl", "da",
    ]


def test_translate(cli_args_da, monkeypatch):
    monkeypatch.setattr('sys.argv', ["prog_name"] + cli_args_da)
    translate()

    indexfile = Path('./example-test/da/index.md')
    assert indexfile.exists()


@pytest.fixture
def cli_args_de():
    return [
        "-d", "./example-test",
        "-p", "./prompts",
        "-sl", "en",
        "-tl", "de",
    ]


def test_translate_de(cli_args_de, monkeypatch):
    monkeypatch.setattr('sys.argv', ["prog_name"] + cli_args_de)
    translate()

    indexfile = Path('./example-test/de/index.md')
    assert indexfile.exists()


@pytest.fixture
def cli_args_fr():
    return [
        "-d", "./example-test",
        "-p", "./prompts",
        "-sl", "en",
        "-tl", "fr",
    ]


def test_translate_fr(cli_args_fr, monkeypatch):
    monkeypatch.setattr('sys.argv', ["prog_name"] + cli_args_fr)
    translate()

    indexfile = Path('./example-test/fr/index.md')
    assert indexfile.exists()
