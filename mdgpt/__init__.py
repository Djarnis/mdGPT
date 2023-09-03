import argparse
import frontmatter
import yaml
import json
import os
import re

from dotenv import load_dotenv
from pathlib import Path

from rich import print
from rich.progress import track

from mdgpt.models import PromptConfig
from mdgpt.models import ChatGPTMessages
from mdgpt.models import ChatGPTPromptMessage

from mdgpt.build import build_step

from mdgpt.utils import get_markdown_files
from mdgpt.utils import get_url_matrices
from mdgpt.utils import log_usage
from mdgpt.utils import DefaultDictFormatter

from mdgpt.translate import save_json_translated
from mdgpt.translate import translate_missing_json
from mdgpt.translate import get_translation_tasks
from mdgpt.translate import translate_markdown_file
from mdgpt.translate import get_target_file
from mdgpt.translate import translate_messages

from mdgpt.image import create_image


load_dotenv()


def cli():
    args = parse_args()
    cfg = PromptConfig.from_yaml(args.prompt, **vars(args))

    funcs = {
        'build': _build,
        'translate': _translate,
        'debug': _debug,
        'image': _image,
        'wip': _translate_wip,
    }

    func = funcs.get(args.action)
    if func is not None:
        func(cfg)
    else:
        print('[red]Unknown action')
        raise SystemExit(1)


def parse_args():
    parser = argparse.ArgumentParser(description='Build and translate markdown files from a prompt configuration file')
    parser.add_argument('action', type=str, help='Action to perform')
    parser.add_argument('prompt', type=str, help='Path to prompt configuration file without extension')
    parser.add_argument('-d', '--dir', dest='dir', type=str, required=False, help='Root directory for language files')
    parser.add_argument('-f', '--file', dest='file', type=str, required=False, help='Optional single file to translate')
    parser.add_argument('-l', '--lang', dest='lang', type=str, required=False, help='Src lang in ISO 639-1 2-letter code')
    parser.add_argument('-s', '--source-dir', dest='source_dir', type=str, help='Optional src dir. Defaults to lang')
    parser.add_argument('-t', '--target', dest='target', type=str, required=False, help='Target lang in ISO 639-1')
    parser.add_argument('--no-cache', help='Flag to ignore cache', dest='ignore_cache', action='store_true')
    return parser.parse_args()


def _build(cfg: PromptConfig):
    print(f'Building {cfg.ROOT_DIR} ...')

    prompt_tokens = completion_tokens = 0
    skips = oks = errors = 0

    wcfg = cfg.WEBSITE_BUILDER
    if wcfg is None:
        print('[red]No website builder config found.')
        exit(1)

    tasks = wcfg.get_tasks()
    total_tasks = len(tasks)

    for i in track(range(total_tasks), description='Building ...'):
        step = tasks[i]

        print_details = f'({i+1}/{total_tasks}) Writing {step.destination} ...'
        print(print_details, end='', flush=True)

        usage, err = build_step(cfg, step)
        if err:
            print(f'[red]{print_details} ERROR:', err)
            errors += 1
        else:
            if usage:
                print(f'[green]{print_details} ok ;)')
                oks += 1
            else:
                print(f'[yellow]{print_details} Skipped!')
                skips += 1

        if usage:
            prompt_tokens += usage['prompt_tokens']
            completion_tokens += usage['completion_tokens']
            log_usage('write_md', cfg.LANGUAGE, step.destination, usage['prompt_tokens'], usage['completion_tokens'])

    print(f'prompt_tokens: {prompt_tokens}')
    print(f'completion_tokens: {completion_tokens}')

    print(f'[yellow]skips: {skips}')
    print(f'[green]oks: {oks}')
    print(f'[red]errors: {errors}')


def _translate(cfg: PromptConfig):

    tasks = get_translation_tasks(cfg)
    total_tasks = len(tasks)

    counters = {'prompt_tokens': 0, 'completion_tokens': 0, 'errors': 0, 'skips': 0, 'oks': 0}

    # Build url maps for each target language
    languages, urls, missing = get_url_matrices(cfg)

    exit_code = 0
    exit_msg = ''

    # Execute translation tasks
    try:
        _translation_loop(cfg, counters, languages, urls, missing, tasks)

    except KeyboardInterrupt:
        print('[red]Aborted!')

    except Exception as e:
        exit_code = 1
        exit_msg = f'An error occurred: {e}'

    print('---')
    print('prompt_tokens:', counters['prompt_tokens'])
    print('completion_tokens:', counters['completion_tokens'])
    print('---')
    print(f'[bold]Tasks: {total_tasks}')
    print(f'[yellow]skips: {counters["skips"]}')
    print(f'[green]oks: {counters["oks"]}')
    print(f'[red]errors: {counters["errors"]}')

    if exit_code > 0:
        print(f'[red]{exit_msg}')
        raise SystemExit(exit_code)


def _translation_loop(cfg: PromptConfig, counters: dict, languages: dict, urls: dict, missing: dict, tasks: list):
    total_tasks = len(tasks)

    for i in track(range(total_tasks), description='Translating ...'):
        task = tasks[i]
        action, target, file = task.split(':')[:3]

        target_lang = languages[target]

        if action == 'js':
            result, usage = _translate_js(cfg, i, total_tasks, urls[target], missing[target], languages[target])
        elif action == 'md':
            result, usage = _translate_md(cfg, i, total_tasks, file, target_lang, urls[target])

        if usage:
            counters['prompt_tokens'] += usage['prompt_tokens']
            counters['completion_tokens'] += usage['completion_tokens']

        if result in ['ok', 'skip', 'error']:
            counters[f'{result}s'] += 1


def _translate_js(cfg: PromptConfig, idx: int, total_tasks: int, url_map: dict, missing: dict, target_lang: dict):
    print_details = f'{idx+1}/{total_tasks} Translating file urls {cfg.LANG.name} ({cfg.LANG.code}) -> {target_lang["name"]} ({target_lang["code"]}) ...'
    print(print_details, end='', flush=True)

    if len(missing) == 0:
        print(f'[yellow]{print_details} Skip!')
        return 'skip', None

    if len(missing) > 0:
        missing_translations, usage = translate_missing_json(cfg, missing, target_lang)

        # Backfill missing translations
        for key, value in missing_translations.items():
            if value is not None and len(value) > 0:
                url_map[key] = value

        # Save url_map ...
        save_json_translated(cfg, url_map, target_lang['code'])
        print(f'[green]{print_details} ok ;)')
        return 'ok', usage


def _translate_md(cfg: PromptConfig, idx: int, total_tasks: int, file: str, target_lang: dict, url_map: dict):
    root = Path(cfg.ROOT_DIR)
    target_path = get_target_file(file, root, target_lang['code'], url_map)

    print_details = f'{idx+1}/{total_tasks} Translating {target_path} ...'
    print(print_details, end='', flush=True)

    if target_path.exists() and cfg.IGNORE_CACHE is False:
        skip = False if cfg.FILE and cfg.FILE == file else True
        if skip:
            print(f'[yellow]{print_details} Skip!')
            return 'skip', None

    if usage := translate_markdown_file(cfg, file, target_lang, url_map):
        log_usage('translate_md', target_lang['code'], file, usage['prompt_tokens'], usage['completion_tokens'])
        print(f'[green]{print_details} ok!')
        return 'ok', usage

    else:
        print(f'[red]{print_details} error!')
        return 'error', None


def _debug(cfg: PromptConfig):
    print('cfg:', cfg)

    unique_matters = []
    root_path = Path(cfg.ROOT_DIR, cfg.SOURCE_DIR or cfg.LANGUAGE)
    files = get_markdown_files(root_path)
    for file in files:
        content = Path(root_path, file).read_text()
        matter = frontmatter.loads(content)
        for k, v in matter.metadata.items():
            if k not in unique_matters:
                unique_matters.append(k)

    print('unique_matters:', sorted(unique_matters))


def _image(cfg: PromptConfig):
    create_image(cfg)


def _translate_wip(cfg: PromptConfig):
    print('Work in Progress ...')

    def _get_url(src_url, target, url_map):
        href = _strip_src_href(src_url)
        if href is not None:
            target_href = url_map.get(href)
            if target_href is None:
                return src_url

            return f'/{target}/{target_href}'
        return src_url

    def _replace_url(item, attr, target, url_map):

        if isinstance(item, str):
            return

        if item.get(attr) is None:
            return

        # url = _get_url(item.get(attr), target, url_map)
        # print('urlurlurl', item.get(attr), url)

        href = _strip_src_href(item.get(attr))

        if href is not None:
            target_href = url_map.get(href)

            if target_href is not None:
                target_href = f'/{target}/{target_href}'
                # print('target_href:', target_href)
                item[attr] = target_href

    def _strip_src_href(href):
        if href is None:
            return None
        prefix = f'/{cfg.LANGUAGE}/'
        if href.startswith(prefix):
            href = href[len(prefix) :]
        href = href.split('#')[0]
        return href

    def _get_sentences_from_files(root, files):
        sentences = []
        for menu_file in files:
            with open(f'{root}/{menu_file}.yaml', 'r') as f:
                menu = yaml.load(f, Loader=yaml.loader.SafeLoader)

            # print('type:', type(menu))
            if isinstance(menu, dict):
                for item in menu:
                    label = menu[item].get('label')
                    if label and label not in sentences:
                        sentences.append(label)

                continue

            for item in menu:
                if item.get('label') and item.get('label') not in sentences:
                    sentences.append(item.get('label'))

                if item.get('featured'):
                    for featured in item.get('featured'):
                        for attr in ['label', 'description', 'button']:
                            if featured.get(attr) and featured.get(attr) not in sentences:
                                sentences.append(featured.get(attr))

                if item.get('sections'):
                    for section in item.get('sections'):
                        if section.get('items'):
                            for xitem in section.get('items'):
                                for attr in ['heading', 'label']:
                                    if xitem.get(attr) and xitem.get(attr) not in sentences:
                                        sentences.append(xitem.get(attr))

                                if xitem.get('bullets'):
                                    for bullet in xitem.get('bullets'):
                                        if bullet not in sentences:
                                            sentences.append(bullet)

                                if xitem.get('button'):
                                    if xitem.get('button').get('label') and xitem.get('button').get('label') not in sentences:
                                        sentences.append(xitem.get('button').get('label'))

                if item.get('aside'):
                    for xitem in item.get('aside'):
                        for attr in ['heading', 'label', 'description', 'button', 'imageAlt']:
                            if xitem.get(attr) and xitem.get(attr) not in sentences:
                                sentences.append(xitem.get(attr))

        return sentences

    def _replace_sentences(menu, translations):

        if isinstance(menu, dict):
            for item in menu:
                label = menu[item].get('label')
                if label:
                    menu[item]['label'] = translations.get(label)
            return

        for item in menu:
            if item.get('label'):
                item['label'] = translations.get(item.get('label'))

            if item.get('featured'):
                for featured in item.get('featured'):
                    for attr in ['label', 'description', 'button']:
                        if featured.get(attr):
                            featured[attr] = translations.get(featured.get(attr))

            if item.get('sections'):
                for section in item.get('sections'):
                    if section.get('items'):
                        for xitem in section.get('items'):
                            for attr in ['heading', 'label']:
                                if xitem.get(attr):
                                    xitem[attr] = translations.get(xitem.get(attr))
                            if xitem.get('bullets'):
                                for i, bullet in enumerate(xitem.get('bullets')):
                                    xitem['bullets'][i] = translations.get(bullet)

                            if xitem.get('button'):
                                if xitem.get('button').get('label'):
                                    xitem['button']['label'] = translations.get(xitem.get('button').get('label'))

            if item.get('aside'):
                for xitem in item.get('aside'):
                    for attr in ['heading', 'label', 'description', 'button', 'imageAlt']:
                        if xitem.get(attr):
                            xitem[attr] = translations.get(xitem.get(attr))

    def _replace_links(menu, url_map):
        if isinstance(menu, dict):
            return

        for item in menu:
            _replace_url(item, 'href', target, url_map)

            if item.get('featured'):
                for featured in item.get('featured'):
                    _replace_url(featured, 'href', target, url_map)

            if item.get('sections'):
                for section in item.get('sections'):
                    if section.get('items'):
                        for xitem in section.get('items'):

                            _replace_url(xitem, 'href', target, url_map)

                            if xitem.get('button'):
                                _replace_url(xitem.get('button'), 'href', target, url_map)

            if item.get('aside'):
                for xitem in item.get('aside'):
                    _replace_url(xitem, 'href', target, url_map)

    def _get_missing(prompt_cfg: PromptConfig, src_dict: dict, target):
        filename = f'{prompt_cfg.LANGUAGE}_{target}.json'
        src_file = Path(f'{prompt_cfg.ROOT_DIR}/.mdgpt-sentences/{filename}')

        if src_file.exists() and prompt_cfg.IGNORE_CACHE is False:
            src_json = json.loads(src_file.read_text())

            for k, v in src_dict.items():
                if src_json.get(k):
                    src_dict[k] = src_json.get(k)

        if src_dict.get(''):
            del src_dict['']

        missing = {}
        for k, v in src_dict.items():
            if k == '':
                continue

            if v is None or v == '':
                missing[k] = ''

        return missing

    languages, url_matrix, missing_matrix = get_url_matrices(cfg)
    menus_files = ['footer', 'main', 'top', 'ui']

    # Get sentences to translate ...
    sentence_matrics = {}
    sentences = _get_sentences_from_files(f'{cfg.ROOT_DIR}/menus/{cfg.LANGUAGE}', menus_files)

    prompt_template = ChatGPTMessages.from_yaml(f'{cfg.ROOT_DIR}/menus')
    prompt_template_messages = prompt_template.messages

    print(f'Translating {len(sentences)} sentences to {len(cfg.TARGET_LANGUAGES)} languages ...')
    print('---------------------------------')
    for target in cfg.TARGET_LANGUAGES:
        print('target:', target)
        translations = {f'{t}': '' for t in sentences}

        # Check cached version
        missing = _get_missing(cfg, translations, target)
        print('missing:', len(missing))

        if len(missing) == 0:
            print('Skip!')
            print('---------------------------')
            sentence_matrics[target] = translations
            continue

        variables = {
            'lang_name': cfg.LANG.name,
            'lang_code': cfg.LANG.code,
            'target_lang_name': languages[target]['name'],
            'target_lang_code': languages[target]['code'],
            'content': json.dumps(missing, indent=2),
        }
        prompt_messages = [
            ChatGPTPromptMessage(
                role=msg.role,
                content=msg.content.format_map(DefaultDictFormatter(variables)).strip(),
            )
            for msg in prompt_template_messages
        ]

        result, usage = translate_messages(cfg, prompt_messages, target)

        # Backfill missing translations
        for key, value in result.items():
            if value is not None and len(value) > 0:
                translations[key] = value

        filename = f'{cfg.LANGUAGE}_{target}.json'
        src_file = Path(f'{cfg.ROOT_DIR}/.mdgpt-sentences/{filename}')
        src_file.parent.mkdir(parents=True, exist_ok=True)
        src_file.write_text(json.dumps(translations, indent=2))

        sentence_matrics[target] = translations

        print('---------------------------')

    # Write yaml files ...
    print('Writing yaml files ...')
    for target in cfg.TARGET_LANGUAGES:
        print('target:', target)

        for menu_file in menus_files:
            root = f'{cfg.ROOT_DIR}/menus/{cfg.LANGUAGE}'
            with open(f'{root}/{menu_file}.yaml', 'r') as f:
                menu = yaml.load(f, Loader=yaml.loader.SafeLoader)

            # Rename values with translations ...
            print('menu_file:', menu_file)

            _replace_sentences(menu, sentence_matrics[target])
            _replace_links(menu, url_matrix[target])

            # Save yaml file ...
            os.makedirs(f'{cfg.ROOT_DIR}/menus/{target}', exist_ok=True)
            with open(f'{cfg.ROOT_DIR}/menus/{target}/{menu_file}.yaml', 'w') as f:
                yaml.dump(menu, f, default_flow_style=False, sort_keys=False)

        print('---------------------------')

    # Replace links in markdown files ...
    # Also: absolute section references ...
    for target in cfg.TARGET_LANGUAGES:
        print(f'Replacing links in markdown files for {target} ...')

        mdfiles = get_markdown_files(Path(cfg.ROOT_DIR, target))
        print('mdfiles:', len(mdfiles))

        for mdfile in mdfiles:
            # load markdown file ...
            md_path = Path(cfg.ROOT_DIR, target, mdfile)
            matter, content = frontmatter.parse(md_path.read_text())
            for k, v in matter.items():
                found_stuff = False
                if k in ['link', 'href', 'url', 'button', 'buttons', 'forum']:
                    # print(f'{mdfile}: k: {k} v: {v}')

                    if isinstance(v, str):
                        # print('v is str')
                        pass

                    elif isinstance(v, dict):
                        # print('v is dict')
                        # for kk, vv in v.items():
                        #     if kk in ['link', 'href', 'url']:
                        #         print('kk:', kk, vv)
                        #         found_stuff = True
                        #         # _replace_url(v, kk, target, url_matrix[target])

                        for attr in ['link', 'href', 'url']:
                            if v.get(attr) is None:
                                continue
                            # print('attr', attr)
                            found_stuff = True
                            _replace_url(v, attr, target, url_matrix[target])

                    elif isinstance(v, list):
                        # print('v is list')
                        for i, item in enumerate(v):
                            if isinstance(item, dict):
                                # print('item is dict')
                                # for kk, vv in item.items():
                                #     if kk in ['link', 'href', 'url']:
                                #         print('kk:', kk, vv)
                                #         found_stuff = True
                                #         # _replace_url(v, kk, target, url_matrix[target])

                                for attr in ['link', 'href', 'url']:
                                    old_val = item.get(attr, None)
                                    if old_val is None:
                                        continue

                                    # print('attr', attr)
                                    found_stuff = True
                                    _replace_url(item, attr, target, url_matrix[target])

                    # if found_stuff:
                    #     print('k found_stuff', k, matter)

                if mdfile.endswith('index.md') and k in ['sections']:
                    # replace absolute urls ...
                    # print('REPLACE ABSURLS!')
                    for i, slug in enumerate(v):
                        src_prefix = f'/{cfg.LANGUAGE}/'
                        target_prefix = f'/{target}/'
                        # print('slug', slug)
                        if slug.startswith((src_prefix, target_prefix)):
                            # TODO: Get correct slug for target language!
                            # 1: Clean up slug: remove /da/**/__
                            # 2: Get translated slug
                            # 3: Replace slug with target prefix, translated slug, and special folder / file
                            new_slug = None
                            pattern = r'^\/(\w{2})(?:\/([^_]+)?)?(__[^\/]+\/[^\/]+)'

                            # Extracting the parts using the regex pattern
                            matches = re.match(pattern, slug)
                            if matches:
                                lang_part, slug_part, component_part = matches.groups()
                                # print('lang_part, slug_part, component_part', lang_part, slug_part, component_part)

                                if slug_part:
                                    if slug_part.endswith('/'):
                                        slug_part = slug_part.rstrip('/')

                                    # print('slug_part', slug_part)

                                    t_slug = url_matrix[target].get(slug_part)
                                    # print('t_slug', t_slug)

                                    if t_slug:
                                        new_slug = f'{target_prefix}{t_slug}/{component_part}'

                                    # print(json.dumps(url_matrix[target], indent=2))
                                else:
                                    new_slug = f'{target_prefix}{component_part}'
                            else:
                                # print('NO MATCH!')
                                pass

                            # print('slug', slug)
                            # print('new_slug', new_slug)
                            # new_slug = f'{target_prefix}{slug[len(src_prefix):]}'
                            if new_slug:
                                matter[k][i] = new_slug

            post = frontmatter.Post(content, **matter)

            md_path.write_text(frontmatter.dumps(post))
