import argparse
import frontmatter

from dotenv import load_dotenv
from pathlib import Path

from rich import print
from rich.progress import track

from mdgpt.utils import log_usage
from mdgpt.models import PromptConfig
from mdgpt.models import get_prompt_config
from mdgpt.build import get_build_tasks
from mdgpt.build import build_step
from mdgpt.utils import get_markdown_files
from mdgpt.utils import get_url_matrices
from mdgpt.translate import save_json_translated
from mdgpt.translate import translate_missing_json
from mdgpt.translate import get_translation_tasks
from mdgpt.translate import translate_markdown_file
from mdgpt.translate import get_target_file
from mdgpt.image import create_image


load_dotenv()


def cli():
    args = parse_args()
    cfg = get_prompt_config(args.prompt, **vars(args))

    funcs = {
        'build': _build,
        'translate': _translate,
        'debug': _debug,
        'image': _image,
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

    tasks = get_build_tasks(wcfg)
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

    prompt_tokens = completion_tokens = 0
    errors = skips = oks = 0

    # Build url maps for each target language
    lang_matrix, url_matrix, missing_matrix = get_url_matrices(cfg)

    exit_code = 0
    exit_msg = ''

    # Execute translation tasks
    try:
        for i in track(range(total_tasks), description='Translating ...'):
            task = tasks[i]
            action, target, file = task.split(':')[:3]

            target_lang = lang_matrix[target]

            if action == 'js':
                result, usage = _translate_js(
                    cfg,
                    i,
                    total_tasks,
                    target,
                    url_matrix[target],
                    missing_matrix[target],
                    lang_matrix[target],
                )
            elif action == 'md':
                result, usage = _translate_md(cfg, i, total_tasks, file, target, target_lang, url_matrix[target])

            if usage:
                prompt_tokens += usage['prompt_tokens']
                completion_tokens += usage['completion_tokens']
                # log_usage(f'translate_{action}', target, file, usage['prompt_tokens'], usage['completion_tokens'])

            if result == 'ok':
                oks += 1
            elif result == 'skip':
                skips += 1
            elif result == 'error':
                errors += 1

    except KeyboardInterrupt:
        print('[red]Aborted!')

    except Exception as e:
        errors += 1
        exit_code = 1
        exit_msg = f'An error occurred: {e}'

    print('---')
    print('prompt_tokens:', prompt_tokens)
    print('completion_tokens:', completion_tokens)
    print('---')
    print(f'[bold]Tasks: {total_tasks}')
    print(f'[yellow]skips: {skips}')
    print(f'[green]oks: {oks}')
    print(f'[red]errors: {errors}')

    if exit_code > 0:
        print(f'[red]{exit_msg}')
        raise SystemExit(exit_code)


def _translate_js(cfg: PromptConfig, i: int, total_tasks: int, target: str, url_map: dict, missing: dict, target_lang: dict):
    print_details = f'{i+1}/{total_tasks} Translating file urls {cfg.LANGUAGE} -> {target} ...'
    print(print_details, end='', flush=True)   # end='\r',

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
        save_json_translated(cfg, url_map, target)
        print(f'[green]{print_details} ok ;)')
        return 'ok', usage


def _translate_md(cfg: PromptConfig, i: int, total_tasks: int, file: str, target: str, target_lang: dict, url_map: dict):
    # Check if file exists
    root = Path(cfg.ROOT_DIR)
    target_path = get_target_file(file, root, target, url_map)

    print_details = f'{i+1}/{total_tasks} Translating {target_path} ...'

    print(print_details, end='', flush=True)   # end='\r',
    if target_path.exists():
        skip = False if cfg.FILE and cfg.FILE == file else True
        if skip:
            print(f'[yellow]{print_details} Skip!')
            return 'skip', None

    if usage := translate_markdown_file(cfg, file, target_lang, url_map):
        log_usage('translate_md', target, file, usage['prompt_tokens'], usage['completion_tokens'])

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
