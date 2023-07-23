import argparse
import glob
import json
import frontmatter
import yaml

from pathlib import Path
from rich import print

from mdgpt.utils import (
    urlize,
    log_usage,
    load_prompt,
    get_chat_response,
    get_gpt_options,
    get_language_name
)


def translate():
    args = get_args()
    prompt_cfg = load_prompt(f'{args.pfile}.yaml')

    source_lang = {
        'code': args.lang,
        'name': get_language_name(args.lang),
        'dir': args.source_dir if args.source_dir else args.lang,
    }
    target_lang = {
        'code': args.target,
        'name': get_language_name(args.target),
        'dir': args.target_dir if args.target_dir else args.target,
    }

    print(f'Translating {source_lang["name"]} ({source_lang["code"]}) to {target_lang["name"]} ({target_lang["code"]})')

    files = get_markdown_files(Path(args.dir, source_lang['dir']))
    print('Files:', len(files))

    # Translate urls
    if prompt_cfg.get('ONLY_INDEXES'):
        url_hash = {urlize(f): '' for f in files if f.endswith('index.md')}
    else:
        url_hash = {urlize(f): '' for f in files}

    url_map, err = translate_json(prompt_cfg['URL_PROMPT'], url_hash, source_lang, target_lang, prompt_cfg.get('MODEL'), args.dir)

    if args.file:
        print('Translating single file', args.file)
        filtered_files = [args.file]
    else:
        filtered_files = filter_markdown_files(files, args.dir, target_lang['dir'], url_map)
        print('filtered_files', len(filtered_files))

    counter = 0
    prompt_tokens = 0
    completion_tokens = 0

    for file in filtered_files:
        print(f'Translating {file} ...', flush=True)   # end='\r',
        if usage := translate_markdown_file(file, args.dir, source_lang, target_lang, url_map, prompt_cfg['MARKDOWN_PROMPT'], prompt_cfg.get('FIELD_KEYS'), prompt_cfg.get('MODEL')):
            prompt_tokens += usage['prompt_tokens']
            completion_tokens += usage['completion_tokens']
            log_usage('translate', args.target, file, usage['prompt_tokens'], usage['completion_tokens'])
            counter += 1

        else:
            print(f'Could not translate {file} ...')

    print('')
    print('counter', counter)
    print('prompt_tokens', prompt_tokens)
    print('completion_tokens', completion_tokens)


def get_args():
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('-d', '--dir', dest='dir', type=str, required=True, help='Root directory for language subdirectories and files')
    parser.add_argument('-p', '--prompts', dest='pfile', type=str, required=True, help='Path to prompt configuration file without extension')
    parser.add_argument('-f', '--file', dest='file', type=str, required=False, help='Optional single file to translate')
    parser.add_argument('-sl', '--lang', dest='lang', type=str, required=True, help='Source language in ISO 639-1 two-letter code')
    parser.add_argument('-sd', '--source-dir', dest='source_dir', type=str, help='Optional Source directory. Defaults to lang')
    parser.add_argument('-tl', '--target', dest='target', type=str, required=True, help='Target language in ISO 639-1 two-letter code')
    parser.add_argument('-td', '--target-dir', dest='target_dir', type=str, help='Optional Target directory. Defaults to target language')

    return parser.parse_args()


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
            'role': msg.get('role', 'user'),
            'content': msg['prompt'].format(
                lang=lang,
                target_lang=target_lang,
                frontmatter=frontmatter,
                content=post.content
            )
        } for msg in prompt_messages
    ]


def get_target_file(file, root, target_dir, url_map):
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


def get_markdown_files(path: Path):
    files = []
    for filepath in glob.iglob(f'{path}/**/*.md', recursive=True):
        relative_path = filepath[len(f'{path}'):]
        files.append(relative_path.lstrip('/'))
    files.sort()
    return files


def translate_markdown_file(file, root_dir, src, target, url_map, prompt_messages, field_keys, gpt_model, ignore_existing=True):
    root = Path(root_dir)

    src_code, src_name, src_dir = src['code'], src['name'], src['dir']
    trg_code, trg_name, trg_dir = target['code'], target['name'], target['dir']

    with open(root / src_dir / file) as f:
        post = frontmatter.load(f)

    target_path = get_target_file(file, root, trg_dir, url_map)
    messages = generate_md_promt(prompt_messages, post, src, target, field_keys)
    options = get_gpt_options(gpt_model)

    try:
        response, usage = get_chat_response(messages, **options)
    except Exception as e:
        raise Exception(f'Could not get response for {file}: {e}')

    try:
        new_matter, new_content = frontmatter.parse(response)
    except Exception as e:
        raise Exception(f'Could not parse {file}: {e}. response: {response}')

    post.content = new_content

    if field_keys is not None and len(field_keys) > 0:
        for field in field_keys:
            if new_matter.get(field):
                post[field] = new_matter[field]
    else:
        post.metadata = new_matter

    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(frontmatter.dumps(post))

    return usage


def translate_json(prompt_messages, json_dict, src, target, gpt_model, root_dir, ignore_existing=True):

    filename = f'translater_urls_{src["code"]}_{target["code"]}.json'
    src_file = Path(f'{root_dir}/_urls/{filename}')

    if src_file.exists():
        print(f'Loading existing file {src_file}')
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
            'role': msg.get('role', 'user'),
            'content': msg.get('prompt').format(lang=src, target_lang=target, content=json.dumps(json_dict, indent=2))
        }
        for msg in prompt_messages
    ]
    options = get_gpt_options(gpt_model)
    response, usage = get_chat_response(messages, **options)
    log_usage('translate_json', target['code'], '', usage['prompt_tokens'], usage['completion_tokens'])

    response_json = json.loads(response)
    # Backfill missing values
    for k, v in response_json.items():
        json_dict[k] = v

    src_file.parent.mkdir(parents=True, exist_ok=True)
    src_file.write_text(json.dumps(json_dict, indent=2))

    return json_dict, None
