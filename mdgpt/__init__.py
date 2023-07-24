import os
import argparse

from mdgpt.build import build
from mdgpt.translate import translate
from mdgpt.misc import list_engines
from dotenv import load_dotenv

load_dotenv()


def cli():
    parser = argparse.ArgumentParser(description='Build and translate markdown files from a prompt configuration file')
    parser.add_argument('action', type=str, help='Action to perform')
    parser.add_argument('prompt', type=str, help='Path to prompt configuration file without extension')
    parser.add_argument('-d', '--dir', dest='dir', type=str, required=False, help='Root directory for language subdirectories and files')
    # parser.add_argument('-p', '--prompts', dest='pfile', type=str, required=False, help='Path to prompt configuration file without extension')
    parser.add_argument('-f', '--file', dest='file', type=str, required=False, help='Optional single file to translate')
    parser.add_argument('-l', '--lang', dest='lang', type=str, required=False, help='Source language in ISO 639-1 two-letter code')
    parser.add_argument('-s', '--source-dir', dest='source_dir', type=str, help='Optional Source directory. Defaults to lang')
    parser.add_argument('-t', '--target', dest='target', type=str, required=False, help='Target language in ISO 639-1 two-letter code')
    # parser.add_argument('-td', '--target-dir', dest='target_dir', type=str, help='Optional Target directory. Defaults to target language')

    args = parser.parse_args()
    print(args)

    arguments = os.sys.argv[1:]
    print(arguments)

    if args.action == 'build':
        build(
            prompt=args.prompt,
            language=args.lang,
            source_dir=args.source_dir,
            root_dir=args.dir,
        )

    elif args.action == 'translate':
        # _translate()
        translate(
            prompt=args.prompt,
            language=args.lang,
            target=args.target,
            source_dir=args.source_dir,
            root_dir=args.dir,
            single_file=args.file,
        )
    elif args.action == 'engines':
        list_engines()
    else:
        print('Unknown action')
