import argparse

from dotenv import load_dotenv
from pathlib import Path

from rich import print
from rich.progress import track

from mdgpt.utils import log_usage
from mdgpt.models import PromptConfig
from mdgpt.models import get_prompt_config_from_yaml
from mdgpt.build import get_build_tasks
from mdgpt.build import build_step
from mdgpt.translate import get_translation_tasks
from mdgpt.utils import get_json_to_translate
from mdgpt.translate import save_json_translated
from mdgpt.utils import get_url_map
from mdgpt.translate import translate_missing_json
from mdgpt.utils import get_lang_dict
from mdgpt.translate import translate_markdown_file
from mdgpt.translate import get_target_file


load_dotenv()


def cli():

    args = parse_args()
    cfg = get_prompt_config_from_yaml(args.prompt, **vars(args))

    source_lang = get_lang_dict(cfg.LANGUAGE)
    source_lang['dir'] = cfg.SOURCE_DIR if cfg.SOURCE_DIR else cfg.LANGUAGE

    if args.action == 'build':
        _build(cfg, source_lang)

    elif args.action == 'translate':
        _translate(cfg, source_lang)

    else:
        print('Unknown action')


def parse_args():
    parser = argparse.ArgumentParser(description='Build and translate markdown files from a prompt configuration file')
    parser.add_argument('action', type=str, help='Action to perform')
    parser.add_argument('prompt', type=str, help='Path to prompt configuration file without extension')
    parser.add_argument('-d', '--dir', dest='dir', type=str, required=False, help='Root directory for language subdirectories and files')
    parser.add_argument('-f', '--file', dest='file', type=str, required=False, help='Optional single file to translate')
    parser.add_argument('-l', '--lang', dest='lang', type=str, required=False, help='Source language in ISO 639-1 two-letter code')
    parser.add_argument('-s', '--source-dir', dest='source_dir', type=str, help='Optional Source directory. Defaults to lang')
    parser.add_argument('-t', '--target', dest='target', type=str, required=False, help='Target language in ISO 639-1 two-letter code')

    return parser.parse_args()


def _build(cfg: PromptConfig, source_lang):
    print(f'Building {cfg.ROOT_DIR} ...')

    prompt_tokens = completion_tokens = 0
    skips = oks = errors = 0

    wcfg = cfg.WEBSITE_BUILDER
    if wcfg is None:
        print('[red]No website builder config found.')
        exit(1)

    tasks = get_build_tasks(wcfg)
    total_tasks = len(tasks)
    print('Tasks:', len(tasks))

    for i in track(range(len(tasks)), description="Building ..."):
        step = tasks[i]

        print_details = f'({i+1}/{total_tasks}) Writing {step.destination} ...'
        print(print_details, end='', flush=True)

        usage, err = build_step(cfg, source_lang, step)
        if err:
            print(f'[red]({print_details} ERROR:', err)
            errors += 1
        else:
            if usage:
                print(f'[green]({print_details} ok ;)')
                oks += 1
            else:
                print(f'[yellow]({print_details} Skipped!')
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


def _translate(cfg: PromptConfig, source_lang):
    tasks = get_translation_tasks(cfg)
    total_tasks = len(tasks)

    prompt_tokens = completion_tokens = 0
    errors = skips = oks = 0

    # Build url maps for each target language
    lang_matrix, url_matrix, missing_matrix = {}, {}, {}
    for target in cfg.TARGET_LANGUAGES:
        url_hashes = get_url_map(cfg)
        url_map, missing = get_json_to_translate(cfg, url_hashes, target)

        url_matrix[target] = url_map
        missing_matrix[target] = missing
        lang_matrix[target] = get_lang_dict(target)

    # Execute translation tasks
    for i in track(range(len(tasks)), description="Translating ..."):
        task = tasks[i]
        action, target, file = task.split(':')[:3]

        if action == 'js':

            url_map = url_matrix[target]
            missing = missing_matrix[target]
            target_lang = lang_matrix[target]

            print_details = f'({i+1}/{total_tasks}) Translating file urls -> {target} ...'
            print(print_details, end='', flush=True)   # end='\r',

            if len(missing) == 0:
                print(f'[yellow]{print_details} Skip!')
                skips += 1

            if len(missing) > 0:
                missing_translations = translate_missing_json(cfg, missing, source_lang, target_lang)

                # Backfill missing translations
                for key, value in missing_translations.items():
                    if value is not None and len(value) > 0:
                        url_map[key] = value

                # Save url_map ...
                save_json_translated(cfg, url_map, target)
                print(f'[green]{print_details} ok ;)')
                oks += 1

        elif action == 'md':

            # Check if file exists
            root = Path(cfg.ROOT_DIR)
            target_path = get_target_file(file, root, target, url_matrix[target])

            print_details = f'({i+1}/{total_tasks}) Translating {file} -> {target_path} ...'

            print(print_details, end='', flush=True)   # end='\r',
            if target_path.exists():
                skip = True
                if cfg.FILE:
                    if cfg.FILE == file:
                        skip = False

                if skip:
                    skips += 1
                    print(f'[yellow]{print_details} Skip!')
                    # time.sleep(0.1)
                    continue

            # if usage := translate_markdown_file(file, prompt_cfg.ROOT_DIR, source_lang, target_lang, url_map, prompt_cfg.MARKDOWN_PROMPT, prompt_cfg.FIELD_KEYS, prompt_cfg.MODEL):
            if usage := translate_markdown_file(cfg, file, source_lang, target_lang, url_matrix[target]):
                prompt_tokens += usage['prompt_tokens']
                completion_tokens += usage['completion_tokens']
                log_usage('translate_md', target, file, usage['prompt_tokens'], usage['completion_tokens'])

                oks += 1

                print(f'[green]{print_details} ok!')
                # print('ok')

            else:
                errors += 1
                print(f'[red]{print_details} error!')
                # print(f'Error...', end='\n')  # end='\r'

        # time.sleep(0.1)  # Simulate work being done

    # with Progress() as progress:
    #     task = progress.add_task("twiddling thumbs", total=len(tasks))
    #     for job in range(len(tasks)):
    #         progress.console.print(f"Working on job #{job}")
    #         # run_job(job)
    #         time.sleep(0.1)
    #         progress.advance(task)

    # text_column = TextColumn("{task.description}", table_column=Column(ratio=1))
    # bar_column = BarColumn(bar_width=None, table_column=Column(ratio=2))
    # progress = Progress(text_column, bar_column, expand=True)

    # with progress:
    #     for n in progress.track(range(100)):
    #         progress.print(n)
    #         time.sleep(0.08)

    print('prompt_tokens:', prompt_tokens)
    print('completion_tokens:', completion_tokens)

    print(f'[yellow]skips: {skips}')
    print(f'[green]oks: {oks}')
    print(f'[red]errors: {errors}')
