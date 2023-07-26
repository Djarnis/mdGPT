import argparse
import frontmatter

from pathlib import Path
from rich import print

from mdgpt.models import PromptConfig
from mdgpt.models import WebsiteBuilder

from mdgpt.utils import (
    load_prompt,
    get_chat_response,
    get_gpt_options,
    get_language_name,
)


def build_step(prompt_cfg: PromptConfig, source_lang, step):

    target_path = Path(prompt_cfg.ROOT_DIR, source_lang['dir'], step.destination)
    if target_path.exists():
        skip = True
        if prompt_cfg.FILE:
            if prompt_cfg.FILE == step.destination:
                skip = False

        if skip:
            return False, None

    wcfg = prompt_cfg.WEBSITE_BUILDER

    title = wcfg.title
    description = wcfg.description

    user_suffix = wcfg.user_suffix.strip()
    system_prompt = wcfg.system_prompt.strip()

    messages = [
        {
            'role': 'system',
            'content': system_prompt.format(lang=source_lang, title=title, description=description)
        },
        {
            'role': 'user',
            'content': '\n'.join([
                step.prompt.format(lang=source_lang, title=title).strip(),
                user_suffix
            ])
        }
    ]

    options = get_gpt_options(prompt_cfg.MODEL)

    try:
        response, usage = get_chat_response(messages, **options)

    except Exception as e:
        # raise Exception(f'Could not get response: {e}')
        # print(f'Could not get response: {e}')
        return None, e

    try:
        new_matter, new_content = frontmatter.parse(response)
    except Exception as e:
        # raise Exception(f'Could not parse: {e}. response: {response}')
        # print(f'Could not parse: {e}. response: {response}')
        return usage, e

    post = frontmatter.Post('')
    post.content = new_content
    post.metadata = new_matter

    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(frontmatter.dumps(post))

    return usage, None


def build(prompt_cfg: PromptConfig):
    print(f'Building {prompt_cfg.ROOT_DIR} ...')

    cfg = prompt_cfg.WEBSITE_BUILDER
    if cfg is None:
        print('No website builder config found.')
        exit(1)

    source_lang = {
        'code': prompt_cfg.LANGUAGE,
        'name': get_language_name(prompt_cfg.LANGUAGE),
        'dir': prompt_cfg.SOURCE_DIR if prompt_cfg.SOURCE_DIR else prompt_cfg.LANGUAGE,
    }

    title = cfg.title
    description = cfg.description

    user_suffix = cfg.user_suffix.strip()
    system_prompt = cfg.system_prompt.strip()

    steps = cfg.steps
    for i, step in enumerate(steps):
        print(f'Building step {i+1}: {step.destination} ...')

        messages = [
            {
                'role': 'system',
                'content': system_prompt.format(lang=source_lang, title=title, description=description)
            },
            {
                'role': 'user',
                'content': '\n'.join([
                    step.prompt.format(lang=source_lang, title=title).strip(),
                    user_suffix
                ])
            }
        ]

        target_path = Path(prompt_cfg.ROOT_DIR, source_lang['dir'], step.destination)
        if target_path.exists():
            print(f'File {target_path} exists. Skipping.')
            continue

        options = get_gpt_options(prompt_cfg.MODEL)

        try:
            response, usage = get_chat_response(messages, **options)
        except Exception as e:
            raise Exception(f'Could not get response: {e}')

        try:
            new_matter, new_content = frontmatter.parse(response)
        except Exception as e:
            raise Exception(f'Could not parse: {e}. response: {response}')

        post = frontmatter.Post('')
        post.content = new_content
        post.metadata = new_matter

        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(frontmatter.dumps(post))


def get_build_tasks(website_builder_cfg: WebsiteBuilder):
    # cfg = prompt_cfg.WEBSITE_BUILDER
    if website_builder_cfg is None:
        print('No website builder config found.')
        exit(1)

    steps = website_builder_cfg.steps
    return steps
    # for i, step in enumerate(steps):
    #     ...
