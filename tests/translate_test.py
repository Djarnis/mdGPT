import pytest
from pathlib import Path
from mdgpt import cli


def get_args(lang):
    return [
        'translate',
        'tests/prompts/prompts',
        '--target',
        lang,
    ]


@pytest.fixture
def cli_args_da():
    return get_args('da')


def test_translate(cli_args_da, monkeypatch):
    monkeypatch.setattr('sys.argv', ['prog_name'] + cli_args_da)

    cli()

    assert Path('./example-test/da/index.md').exists()


@pytest.fixture
def cli_args_da_file():
    args = get_args('da')
    args.extend(['--file', 'index.md'])
    return args


def test_translate_file(cli_args_da_file, monkeypatch):
    target_path = Path('./example-test/da/index.md')
    url_path = Path('./example-test/.mdgpt-urls/en_da.json')

    [f.unlink() for f in [target_path, url_path] if f.exists()]

    monkeypatch.setattr('sys.argv', ['prog_name'] + cli_args_da_file)

    cli()

    assert Path(target_path).exists()
    assert Path(url_path).exists()


@pytest.fixture
def cli_args_de():
    return get_args('de')


def test_translate_de(cli_args_de, monkeypatch):
    monkeypatch.setattr('sys.argv', ['prog_name'] + cli_args_de)

    cli()

    assert Path('./example-test/de/index.md').exists()


@pytest.fixture
def cli_args_fr():
    return get_args('fr')


def test_translate_fr(cli_args_fr, monkeypatch):
    monkeypatch.setattr('sys.argv', ['prog_name'] + cli_args_fr)

    cli()

    assert Path('./example-test/fr/index.md').exists()


@pytest.fixture
def cli_args_xx():
    return get_args('xx')


def test_translate_xx(cli_args_xx, monkeypatch):
    monkeypatch.setattr('sys.argv', ['prog_name'] + cli_args_xx)

    with pytest.raises(SystemExit) as pytest_wrapped_e:
        cli()

    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code == 1
