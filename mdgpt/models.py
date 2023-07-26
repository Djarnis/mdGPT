from pydantic_core.core_schema import FieldValidationInfo
from pydantic import BaseModel, ValidationError, field_validator
from typing import List, Optional
import yaml

from pathlib import Path


class ChatGPTModel(BaseModel):
    temperature: float=0.2
    engine: str='gpt-3.5-turbo'
    max_tokens: int=1024*2


class ChatGPTPrompt(BaseModel):
    role: str='user'
    prompt: str


class ChatGPTStepPrompt(BaseModel):
    role: str='user'
    prompt: str
    destination: str


class WebsiteBuilder(BaseModel):
    title: str=''
    description: str=''
    user_suffix: str=''
    system_prompt: str=''
    steps: List[ChatGPTStepPrompt]


class PromptConfig(BaseModel):
    LANGUAGE: str=None
    ROOT_DIR: str=None
    SOURCE_DIR: str=None
    TARGET_LANGUAGES: List[str]=[]
    MODEL: ChatGPTModel=None
    WEBSITE_BUILDER: WebsiteBuilder=None
    URL_PROMPT: List[ChatGPTPrompt]
    MARKDOWN_PROMPT: List[ChatGPTPrompt]
    ONLY_INDEXES: bool=False
    FILE: str=None
    FIELD_KEYS: List[str]=None

    @field_validator('LANGUAGE')
    def language_must_be_iso(cls, v):
        if len(v) != 2:
            raise ValueError('LANGUAGE must be an ISO 639-1 two-letter language code')
        return v


def get_prompt_config_from_yaml(prompt_file: str, **kwargs) -> PromptConfig:
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

    try:
        cfg = PromptConfig(**prompt)

    except ValidationError as e:
        print(e)
        exit(1)

    return cfg
