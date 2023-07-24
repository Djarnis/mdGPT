import argparse
import frontmatter

from pathlib import Path
from rich import print

from mdgpt.utils import (
    load_prompt,
    get_chat_response,
    get_gpt_options,
    get_language_name,
)


def build(prompt: str, language: str=None, source_dir: str=None, root_dir: str=None):
    print(f'Building {prompt} ...')

    prompt_cfg = load_prompt(f'{prompt}.yaml')

    if language is None:
        language = prompt_cfg['LANGUAGE']

    if root_dir is None:
        root_dir = prompt_cfg['ROOT_DIR']

    cfg = prompt_cfg.get('WEBSITE_BUILDER')
    if cfg is None:
        print('No website builder config found.')
        exit(1)

    source_lang = {
        'code': language,
        'name': get_language_name(language),
        'dir': source_dir if source_dir else language,
    }

    title = cfg.get('title', '')
    description = cfg.get('description', '')

    user_suffix = cfg.get('user_suffix', '').strip()
    system_prompt = cfg.get('system_prompt').strip()

    steps = cfg.get('steps')
    for i, step in enumerate(steps):
        print(f'Building step {i+1}: {step["destination"]} ...')

        post = frontmatter.Post('')
        messages = [
            {
                'role': 'system',
                'content': system_prompt.format(lang=source_lang, title=title, description=description)
            },
            {
                'role': 'user',
                'content': '\n'.join([
                    step.get('prompt').format(lang=source_lang, title=title).strip(),
                    user_suffix
                ])
            }
        ]

        target_path = Path(root_dir, source_lang['dir'], step['destination'])
        if target_path.exists():
            print(f'File {target_path} exists. Skipping.')
            continue

        options = get_gpt_options(prompt_cfg.get('MODEL'))

        try:
            response, usage = get_chat_response(messages, **options)
        except Exception as e:
            raise Exception(f'Could not get response: {e}')

        try:
            new_matter, new_content = frontmatter.parse(response)
        except Exception as e:
            raise Exception(f'Could not parse: {e}. response: {response}')

        post.content = new_content
        post.metadata = new_matter

        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(frontmatter.dumps(post))
