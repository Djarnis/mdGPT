import json
import frontmatter
import yaml

from pathlib import Path
from rich import print
from typing import List

from mdgpt.models import PromptConfig
from mdgpt.models import ChatGPTPromptMessage
from mdgpt.utils import get_url_map
from mdgpt.utils import (
    urlize,
    log_usage,
    get_chat_response,
    get_gpt_options,
    get_markdown_files,
)


def get_translation_tasks(prompt_cfg: PromptConfig):
    tasks = []
    for target in prompt_cfg.TARGET_LANGUAGES:
        url_hash = get_url_map(prompt_cfg)
        tasks.append(f'js:{target}:{prompt_cfg.LANGUAGE}_{target}')

        if prompt_cfg.FILE:
            tasks.append(f'md:{target}:{prompt_cfg.FILE}')
            continue
        else:
            for k, v in url_hash.items():
                if not k.endswith('.md'):
                    if len(k) > 0:
                        k = f'{k}/index.md'
                    else:
                        k = f'{k}index.md'
                tasks.append(f'md:{target}:{k}')

        files = get_markdown_files(Path(prompt_cfg.ROOT_DIR, prompt_cfg.SOURCE_DIR or prompt_cfg.LANGUAGE))
        for f in files:
            if f.endswith('README.md'):
                continue

            if f.endswith('index.md'):
                f = f.rstrip('index.md').rstrip('/')

            if url_hash.get(f) is None:
                tasks.append(f'md:{target}:{f}')

    return tasks


def generate_frontmatter(post, field_keys, field_keys_delete=None):
    field_dict = {}
    if field_keys is not None and len(field_keys) > 0:
        for field in field_keys:
            # print('field', field)
            # print('type field', type(field))

            if isinstance(field, dict):
                # print('field.keys()', field.keys())

                for k in field.keys():
                    # print('k', k)
                    field_vals = field.get(k)
                    # print('field_vals', field_vals)

                    if post.get(k) is not None:
                        # print('k is something!')
                        val = post.get(k)
                        # print('val', type(val))

                        if isinstance(val, list):
                            # print('val is a list!')

                            field_dict[k] = []

                            for v in val:
                                # print('v', v)
                                # print('v', type(v))

                                if isinstance(v, dict):
                                    # print('v is a dict!')
                                    list_dict = {}
                                    for fv in field_vals:
                                        # print('fv', fv)
                                        if v.get(fv) is not None:
                                            # print('fv is something!', v.get(fv))
                                            # field_dict[fv] = v.get(fv)
                                            list_dict[fv] = v.get(fv)
                                    field_dict[k].append(list_dict)

                        # field_value = post[k]
                        # field_dict[k] = field_value

                # continue ...
                continue

            if field in post.keys():
                # print('wooop')
                if post[field] is not None:
                    field_value = post[field]
                    field_dict[field] = field_value
    else:
        field_dict = post.metadata

    # print('field_dict', field_dict)

    if field_keys_delete is not None and len(field_keys_delete) > 0:
        for field in field_keys_delete:
            if field in field_dict.keys():
                del field_dict[field]

    frontmatter = yaml.dump(field_dict)
    # print('frontmatter', frontmatter)
    return frontmatter


def generate_md_promt(prompt_messages, post, lang, target_lang, field_keys, field_keys_delete=None):
    frontmatter = generate_frontmatter(post, field_keys, field_keys_delete)

    return [
        {
            'role': msg.role,
            'content': msg.prompt.format(
                # lang=lang,
                lang_name=lang.name,
                lang_code=lang.code,
                target_lang=target_lang,
                target_lang_name=target_lang['name'],
                target_lang_code=target_lang['code'],
                frontmatter=frontmatter,
                content=post.content,
            ),
        }
        for msg in prompt_messages
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


def translate_markdown_file(prompt_cfg: PromptConfig, file, target, url_map, ignore_existing=True):
    root = Path(prompt_cfg.ROOT_DIR)

    trg_dir = target['dir']

    with open(root / prompt_cfg.LANG.directory / file) as f:
        post = frontmatter.load(f)

    target_path = get_target_file(file, root, trg_dir, url_map)
    messages = generate_md_promt(
        prompt_cfg.MARKDOWN_PROMPT, post, prompt_cfg.LANG, target, prompt_cfg.FIELD_KEYS, prompt_cfg.FIELD_KEYS_DELETE
    )
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

    if prompt_cfg.FIELD_KEYS_DELETE is not None and len(prompt_cfg.FIELD_KEYS_DELETE) > 0:
        for field in prompt_cfg.FIELD_KEYS_DELETE:
            if post.get(field):
                del post[field]

    if prompt_cfg.FIELD_KEYS is not None and len(prompt_cfg.FIELD_KEYS) > 0:
        for field in prompt_cfg.FIELD_KEYS:
            if isinstance(field, dict):
                for k in field.keys():
                    field_vals = field.get(k)
                    if post.get(k) is not None:
                        val = post.get(k)
                        if isinstance(val, list):
                            for ix, v in enumerate(val):
                                if isinstance(v, dict):
                                    for fv in field_vals:
                                        if new_matter[k][ix].get(fv) is not None:
                                            post[k][ix][fv] = new_matter[k][ix][fv]

                                        # print('post[k]', post[k])
                            # print('Continuing ...')
                            continue
            if isinstance(field, str):
                if new_matter.get(field):
                    post[field] = new_matter[field]
    else:
        post.metadata = new_matter

    target_path.parent.mkdir(parents=True, exist_ok=True)
    # print('Writing to', target_path)
    target_path.write_text(frontmatter.dumps(post))

    return usage


def save_json_translated(prompt_cfg: PromptConfig, json_dict: dict, target: dict):
    filename = f'{prompt_cfg.LANGUAGE}_{target}.json'
    src_file = Path(f'{prompt_cfg.ROOT_DIR}/.mdgpt-urls/{filename}')

    src_file.parent.mkdir(parents=True, exist_ok=True)
    src_file.write_text(json.dumps(json_dict, indent=2))


def translate_missing_json(prompt_cfg: PromptConfig, json_dict, target):
    content = json.dumps(json_dict, indent=2)
    messages = [
        ChatGPTPromptMessage(
            role=msg.role,
            content=msg.prompt.format(
                lang_name=prompt_cfg.LANG.name,
                lang_code=prompt_cfg.LANG.code,
                target_lang=target,
                target_lang_name=target['name'],
                target_lang_code=target['code'],
                content=content,
            ),
        )
        for msg in prompt_cfg.URL_PROMPT
    ]

    return translate_messages(prompt_cfg, messages, target['code'])


def translate_messages(prompt_cfg: PromptConfig, messages: List[ChatGPTPromptMessage], target: str):
    options = get_gpt_options(prompt_cfg.MODEL)
    prompts = [m.model_dump() for m in messages]
    response, usage = get_chat_response(prompts, **options)
    log_usage(
        'translate_json',
        target,
        f'{prompt_cfg.LANG.code}_{target}',
        usage['prompt_tokens'],
        usage['completion_tokens'],
    )
    return json.loads(response), usage
