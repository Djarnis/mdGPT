import pytest
from pathlib import Path
from mdgpt import cli

# pytest tests/translate_test.py -s


def get_args(lang):
    return [
        'translate',
        'tests/prompts',
        '--target', lang,
    ]


@pytest.fixture
def cli_args_da():
    return get_args('da')


def test_translate(cli_args_da, monkeypatch):
    monkeypatch.setattr('sys.argv', ["prog_name"] + cli_args_da)
    cli()

    indexfile = Path('./example-test/da/index.md')
    assert indexfile.exists()


@pytest.fixture
def cli_args_da_file():
    args = get_args('da')
    args.extend(['--file', 'index.md'])
    return args


def test_translate_file(cli_args_da_file, monkeypatch):
    target_path = './example-test/da/index.md'
    url_path = './example-test/.mdgpt-urls/en_da.json'

    for f in [target_path, url_path]:
        file_path = Path(f)
        if file_path.exists():
            file_path.unlink()

    monkeypatch.setattr('sys.argv', ["prog_name"] + cli_args_da_file)
    cli()

    indexfile = Path(target_path)
    assert indexfile.exists()

    indexfile = Path(url_path)
    assert indexfile.exists()


@pytest.fixture
def cli_args_de():
    return get_args('de')


def test_translate_de(cli_args_de, monkeypatch):
    monkeypatch.setattr('sys.argv', ["prog_name"] + cli_args_de)
    cli()

    indexfile = Path('./example-test/de/index.md')
    assert indexfile.exists()


@pytest.fixture
def cli_args_fr():
    return get_args('fr')


def test_translate_fr(cli_args_fr, monkeypatch):
    monkeypatch.setattr('sys.argv', ["prog_name"] + cli_args_fr)
    cli()

    indexfile = Path('./example-test/fr/index.md')
    assert indexfile.exists()
