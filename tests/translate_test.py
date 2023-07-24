import pytest
from pathlib import Path
from mdgpt import cli


@pytest.fixture
def cli_args_da():
    return [
        "translate",
        "tests/prompts",
        "--target", "da",
    ]


def test_translate(cli_args_da, monkeypatch):
    monkeypatch.setattr('sys.argv', ["prog_name"] + cli_args_da)
    cli()

    indexfile = Path('./example-test/da/index.md')
    assert indexfile.exists()


@pytest.fixture
def cli_args_de():
    return [
        "translate",
        "tests/prompts",
        "--target", "de",
    ]


def test_translate_de(cli_args_de, monkeypatch):
    monkeypatch.setattr('sys.argv', ["prog_name"] + cli_args_de)
    cli()

    indexfile = Path('./example-test/de/index.md')
    assert indexfile.exists()


@pytest.fixture
def cli_args_fr():
    return [
        "translate",
        "tests/prompts",
        "--target", "fr",
    ]


def test_translate_fr(cli_args_fr, monkeypatch):
    monkeypatch.setattr('sys.argv', ["prog_name"] + cli_args_fr)
    cli()

    indexfile = Path('./example-test/fr/index.md')
    assert indexfile.exists()
