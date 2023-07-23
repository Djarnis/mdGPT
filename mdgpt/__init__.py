from mdgpt.build import build as _build
from mdgpt.translate import translate as _translate
from mdgpt.misc import list_engines
from dotenv import load_dotenv

load_dotenv()


def build():
    _build()


def translate():
    _translate()


def engines():
    list_engines()
