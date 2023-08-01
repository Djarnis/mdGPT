import yaml
import pycountry

from pydantic import BaseModel, ValidationError, field_validator
from typing import List


class LangModel(BaseModel):
    code: str
    name: str
    directory: str


class ChatGPTModel(BaseModel):
    temperature: float = 0.2
    engine: str = 'gpt-3.5-turbo'
    max_tokens: int = 1024 * 2


class ChatGPTPrompt(BaseModel):
    role: str = 'user'
    prompt: str


class ChatGPTStepPrompt(BaseModel):
    role: str = 'user'
    prompt: str
    destination: str


class WebsiteBuilder(BaseModel):
    title: str = ''
    description: str = ''
    user_suffix: str = ''
    system_prompt: str = ''
    steps: List[ChatGPTStepPrompt]
    variables: dict = {}


class PromptConfig(BaseModel):
    LANGUAGE: str = None
    ROOT_DIR: str = None
    SOURCE_DIR: str = None
    TARGET_LANGUAGES: List[str] = []
    MODEL: ChatGPTModel = None
    WEBSITE_BUILDER: WebsiteBuilder = None
    URL_PROMPT: List[ChatGPTPrompt]
    MARKDOWN_PROMPT: List[ChatGPTPrompt]
    ONLY_INDEXES: bool = False
    FILE: str = None
    FIELD_KEYS: List[str] = None
    FIELD_KEYS_DELETE: List[str] = None
    LANG: LangModel = None
    IGNORE_CACHE: bool = False

    @field_validator('LANGUAGE')
    def language_must_be_iso(cls, v):
        if len(v) != 2:
            raise ValueError('LANGUAGE must be an ISO 639-1 two-letter language code')
        return v

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        if self.LANGUAGE is not None:
            self.LANG = LangModel(
                code=self.LANGUAGE,
                name=get_language_name(self.LANGUAGE),
                directory=self.SOURCE_DIR or self.LANGUAGE,
            )


def get_language_name(lang_code):
    lang = pycountry.languages.get(alpha_2=lang_code)
    if lang is None:
        print(f'Language {lang_code} not found :/', lang)
        exit(1)
    return lang.name


def get_prompt_config(prompt_file: str, **kwargs) -> PromptConfig:
    try:
        with open(f'{prompt_file}.yaml', 'r') as f:
            prompt = yaml.load(f, Loader=yaml.loader.SafeLoader)

    except FileNotFoundError:
        print(f'Prompt file {prompt_file} not found.')
        exit(1)

    if kwargs.get('lang'):
        prompt['LANGUAGE'] = kwargs['lang']

    if kwargs.get('source_dir'):
        prompt['SOURCE_DIR'] = kwargs['source_dir']

    if kwargs.get('dir'):
        prompt['ROOT_DIR'] = kwargs['dir']

    if kwargs.get('target'):
        prompt['TARGET_LANGUAGES'] = [kwargs['target']]

    if kwargs.get('file'):
        prompt['FILE'] = kwargs['file']

    if kwargs.get('ignore_cache'):
        prompt['IGNORE_CACHE'] = True

    try:
        cfg = PromptConfig(**prompt)

    except ValidationError as e:
        print(f'[red]{e}')
        exit(1)

    return cfg
