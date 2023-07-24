import os
import yaml
import pycountry
import openai

from pathlib import Path


def urlize(text):
    if text.endswith('index.md'):
        text = text[:-9]
    return text


def log_usage(action, target, file, prompt_tokens, completion_tokens):
    logger = Path(f'./.mdgpt-usage/usage_{action}.csv')
    if not logger.exists():
        logger.parent.mkdir(parents=True, exist_ok=True)
        logger.write_text('target;file;prompt_tokens;completion_tokens\n')

    with logger.open('a') as f:
        f.write(f'{target};{file};{prompt_tokens};{completion_tokens}\n')


def load_prompt(prompt_file):
    try:
        with open(prompt_file, 'r') as f:
            prompt = yaml.load(f, Loader=yaml.loader.SafeLoader)
    except FileNotFoundError:
        print(f'Prompt file {prompt_file} not found.')
        exit(1)

    return prompt


def get_chat_response(messages, model='gpt-3.5-turbo', temperature=0.2, max_tokens=1024*2, n=1):
    if os.getenv('OPENAI_API_KEY') is None:
        print('Please set OPENAI_API_KEY and OPENAI_ORGANIZATION environment variables.')
        exit(1)
    openai.api_key = os.getenv('OPENAI_API_KEY')
    try:
        completions = openai.ChatCompletion.create(
            model=model,
            max_tokens=max_tokens,
            n=n,
            stop=None,
            temperature=temperature,
            messages=messages,
        )

        message = completions.choices[0].message.content
        usage = completions.usage.to_dict()

        return message, usage

    except openai.error.AuthenticationError as e:
        print(f'OpenAI AuthenticationError: {e}')
        exit(1)

    except openai.error.OpenAIError as e:
        print(f'OpenAI Error: {e}')
        exit(1)

    except Exception as e:
        print(f'An error occurred: {e}')
        exit(1)

def get_gpt_options(gpt_model):
    options = {}
    if gpt_model:
        if gpt_model.get('engine'):
            options['model'] = gpt_model['engine']
        if gpt_model.get('temperature'):
            options['temperature'] = gpt_model['temperature']
        if gpt_model.get('max_tokens'):
            options['max_tokens'] = gpt_model['max_tokens']
    return options


def get_language_name(lang_code):
    try:
        lang = pycountry.languages.get(alpha_2=lang_code)
    except Exception as e:
        print(f'An error occurred: {e}')
        exit(1)

    if lang is None:
        print(f'Language {lang_code} not found.', lang)
        exit(1)

    return lang.name

