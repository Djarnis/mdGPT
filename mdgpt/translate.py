import argparse
import glob
import json
import frontmatter
import yaml

from pathlib import Path
from rich import print

from mdgpt.models import PromptConfig
from mdgpt.utils import get_lang_dict
from mdgpt.utils import get_url_map
from mdgpt.utils import (
    urlize,
    log_usage,
    load_prompt,
    get_chat_response,
    get_gpt_options,
    get_language_name
)


def get_translation_tasks(prompt_cfg: PromptConfig):
    source_lang = get_lang_dict(prompt_cfg.LANGUAGE)
    source_lang['dir'] = prompt_cfg.SOURCE_DIR if prompt_cfg.SOURCE_DIR else prompt_cfg.LANGUAGE

    tasks = []
    for target in prompt_cfg.TARGET_LANGUAGES:
        # target_lang = get_lang_dict(target)

        url_hash = get_url_map(prompt_cfg)

        tasks.append(f'js:{target}:{prompt_cfg.LANGUAGE}_{target}')

        if prompt_cfg.FILE:
            tasks.append(f'md:{target}:{prompt_cfg.FILE}' )
        else:
            for k, v in url_hash.items():
                if not k.endswith('.md'):
                    if len(k) > 0:
                        k = f'{k}/index.md'
                    else:
                        k = f'{k}index.md'
                tasks.append(f'md:{target}:{k}')
            # tasks.extend([f'md:{target}:{k}' for k, v in url_hash.items()])

    return tasks


def translate(prompt_cfg: PromptConfig):
    source_lang = {
        'code': prompt_cfg.LANGUAGE,
        'name': get_language_name(prompt_cfg.LANGUAGE),
        'dir': prompt_cfg.SOURCE_DIR if prompt_cfg.SOURCE_DIR else prompt_cfg.LANGUAGE,
    }

    tasks = []
    for target in prompt_cfg.TARGET_LANGUAGES:
        target_lang = {
            'code': target,
            'name': get_language_name(target),
            'dir': target,
        }

        print(f'Translating {source_lang["name"]} ({source_lang["code"]}) to {target_lang["name"]} ({target_lang["code"]}) ...')

        files = get_markdown_files(Path(prompt_cfg.ROOT_DIR, source_lang['dir']))
        print('Files:', len(files))

        # Translate urls
        if prompt_cfg.ONLY_INDEXES:
            url_hash = {urlize(f): '' for f in files if f.endswith('index.md')}
        else:
            url_hash = {urlize(f): '' for f in files}

        url_map, err = translate_json(prompt_cfg, url_hash, source_lang, target_lang)

        if prompt_cfg.FILE:
            print('Translating single file', prompt_cfg.FILE)
            filtered_files = [prompt_cfg.FILE]
        else:
            filtered_files = filter_markdown_files(files, prompt_cfg.ROOT_DIR, target_lang['dir'], url_map)
            print('filtered_files', len(filtered_files))

        counter = 0
        prompt_tokens = 0
        completion_tokens = 0

        for file in filtered_files:
            print(f'Translating {file} ...', flush=True)   # end='\r',
            # if usage := translate_markdown_file(file, prompt_cfg.ROOT_DIR, source_lang, target_lang, url_map, prompt_cfg.MARKDOWN_PROMPT, prompt_cfg.FIELD_KEYS, prompt_cfg.MODEL):
            if usage := translate_markdown_file(prompt_cfg, file, source_lang, target_lang, url_map):
                prompt_tokens += usage['prompt_tokens']
                completion_tokens += usage['completion_tokens']
                log_usage('translate_md', target, file, usage['prompt_tokens'], usage['completion_tokens'])
                counter += 1

            else:
                print(f'Could not translate {file} ...')

        print('')
        print('counter', counter)
        print('prompt_tokens', prompt_tokens)
        print('completion_tokens', completion_tokens)


def generate_frontmatter(post, field_keys):
    field_dict = {}
    if field_keys is not None and len(field_keys) > 0:
        for field in field_keys:
            if field in post.keys():
                if post[field] is not None:
                    field_value = post[field]
                    field_dict[field] = field_value
    else:
        field_dict = post.metadata
    frontmatter = yaml.dump(field_dict)
    return frontmatter


def generate_md_promt(prompt_messages, post, lang, target_lang, field_keys):
    frontmatter = generate_frontmatter(post, field_keys)
    return [
        {
            'role': msg.role,
            'content': msg.prompt.format(
                lang=lang,
                target_lang=target_lang,
                frontmatter=frontmatter,
                content=post.content
            )
        } for msg in prompt_messages
    ]


def get_target_file(file, root, target_dir, url_map) -> Path:
    file_dirs = file.split('/')
    # If file is in a "special" directory, look up best match in url_map ...
    if len(file_dirs) > 1:
        if file_dirs[-2] in ['__sections', '__process']:
            parent_dir = '/'.join(file_dirs[:-2])
            parent_dir_translated = url_map.get(parent_dir)
            if parent_dir_translated:
                target_file = root / target_dir / parent_dir_translated / '/'.join(file_dirs[-2:])
                return target_file

    # Check url_map
    url_file = urlize(file)
    url_mapped = url_map.get(url_file)
    if url_mapped:
        dirs = url_mapped.split('/')
        url_file = dirs[-1]
        url_file_parts = url_file.split('.')
        if len(url_file_parts) > 1:
            # Replace extension
            dirs[-1] = f'{url_file_parts[0]}.md'
        else:
            # Append index.md
            dirs.append('index.md')
        url_mapped = '/'.join(dirs)

        target_file = root / target_dir / url_mapped
        return target_file

    return root / target_dir / file


def filter_markdown_files(files, root, target_dir, url_map):
    root = Path(root)
    filtered_files = []
    for file in files:
        target_file = get_target_file(file, root, target_dir, url_map)

        if str(target_file).endswith('README.md'):
            continue

        if target_file.exists():
            continue

        filtered_files.append(file)
    return filtered_files




def translate_markdown_file(prompt_cfg: PromptConfig, file, src, target, url_map, ignore_existing=True):
    root = Path(prompt_cfg.ROOT_DIR)

    src_code, src_name, src_dir = src['code'], src['name'], src['dir']
    trg_code, trg_name, trg_dir = target['code'], target['name'], target['dir']

    with open(root / src_dir / file) as f:
        post = frontmatter.load(f)

    target_path = get_target_file(file, root, trg_dir, url_map)
    messages = generate_md_promt(prompt_cfg.MARKDOWN_PROMPT, post, src, target, prompt_cfg.FIELD_KEYS)
    options = get_gpt_options(prompt_cfg.MODEL)

    try:
        response, usage = get_chat_response(messages, **options)
    except Exception as e:
        # raise Exception(f'Could not get response for {file}: {e}')
        print(f'Could not get response for {file}: {e}')
        return


    try:
        new_matter, new_content = frontmatter.parse(response)
    except Exception as e:
        # raise Exception(f'Could not parse {file}: {e}. response: {response}')
        print(f'Could not parse {file}: {e}. response: {response}')
        return

    post.content = new_content

    if prompt_cfg.FIELD_KEYS is not None and len(prompt_cfg.FIELD_KEYS) > 0:
        for field in prompt_cfg.FIELD_KEYS:
            if new_matter.get(field):
                post[field] = new_matter[field]
    else:
        post.metadata = new_matter

    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(frontmatter.dumps(post))

    return usage




def save_json_translated(prompt_cfg: PromptConfig, json_dict, target):
    filename = f'{prompt_cfg.LANGUAGE}_{target}.json'
    src_file = Path(f'{prompt_cfg.ROOT_DIR}/.mdgpt-urls/{filename}')

    src_file.parent.mkdir(parents=True, exist_ok=True)
    src_file.write_text(json.dumps(json_dict, indent=2))


def translate_missing_json(prompt_cfg: PromptConfig, json_dict, src, target):
    messages = [
        {
            'role': msg.role,
            'content': msg.prompt.format(lang=src, target_lang=target, content=json.dumps(json_dict, indent=2))
        }
        for msg in prompt_cfg.URL_PROMPT
    ]
    options = get_gpt_options(prompt_cfg.MODEL)
    response, usage = get_chat_response(messages, **options)
    log_usage('translate_json', target['code'], f'{src["code"]}_{target["code"]}', usage['prompt_tokens'], usage['completion_tokens'])

    response_json = json.loads(response)

    return response_json

def translate_json(prompt_cfg: PromptConfig, json_dict, src, target, ignore_existing=True):

    filename = f'{src["code"]}_{target["code"]}.json'
    src_file = Path(f'{prompt_cfg.ROOT_DIR}/.mdgpt-urls/{filename}')

    if src_file.exists():
        # print(f'Loading existing file {src_file}')
        src_json = json.loads(src_file.read_text())

        for k, v in json_dict.items():
            if src_json.get(k):
                json_dict[k] = src_json.get(k)

    if json_dict.get(''):
        del json_dict['']

    missing = {}
    for k, v in json_dict.items():
        if k == '':
            # print('This is empty', k, v)
            continue

        if v is None or v == '':
            # print('This is none or empty', k, v)
            missing[k] = v

    print('missing', len(missing), missing)
    if len(missing) == 0:
        return json_dict, None

    messages = [
        {
            'role': msg.role,
            'content': msg.prompt.format(lang=src, target_lang=target, content=json.dumps(json_dict, indent=2))
        }
        for msg in prompt_cfg.URL_PROMPT
    ]
    options = get_gpt_options(prompt_cfg.MODEL)
    response, usage = get_chat_response(messages, **options)
    log_usage('translate_json', target['code'], '', usage['prompt_tokens'], usage['completion_tokens'])

    response_json = json.loads(response)
    # Backfill missing values
    for k, v in response_json.items():
        json_dict[k] = v

    src_file.parent.mkdir(parents=True, exist_ok=True)
    src_file.write_text(json.dumps(json_dict, indent=2))

    return json_dict, None
