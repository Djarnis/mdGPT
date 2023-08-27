import frontmatter

from pathlib import Path
from rich import print

from mdgpt.models import PromptConfig
from mdgpt.models import WebsiteBuilder

from mdgpt.utils import (
    get_chat_response,
    get_gpt_options,
    DefaultDictFormatter,
)


def build_step(prompt_cfg: PromptConfig, step):
    target_path = Path(prompt_cfg.ROOT_DIR, prompt_cfg.LANG.directory, step.destination)
    if target_path.exists():
        skip = False if prompt_cfg.FILE and prompt_cfg.FILE == step.destination else True
        if skip:
            return False, None

    wcfg = prompt_cfg.WEBSITE_BUILDER

    user_suffix = wcfg.user_suffix.strip()
    system_prompt = wcfg.system_prompt.strip()

    step_prompt = '\n'.join(
        [
            step.prompt.strip(),
            user_suffix,
        ]
    )

    variables = wcfg.variables

    variables['lang_name'] = prompt_cfg.LANG.name
    variables['lang_code'] = prompt_cfg.LANG.code

    messages = [
        {
            'role': 'system',
            'content': system_prompt.format_map(DefaultDictFormatter(variables)).strip(),
        },
        {'role': 'user', 'content': step_prompt.format_map(DefaultDictFormatter(variables))},
    ]

    options = get_gpt_options(prompt_cfg.MODEL)

    try:
        response, usage = get_chat_response(messages, **options)

    except Exception as e:
        return None, e

    try:
        new_matter, new_content = frontmatter.parse(response)
    except Exception as e:
        return usage, e

    post = frontmatter.Post(new_content, **new_matter)

    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(frontmatter.dumps(post))

    return usage, None
