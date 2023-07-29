import os
import openai
import hashlib
import requests
from io import BytesIO
from slugify import slugify
from pathlib import Path

from PIL import Image

from mdgpt.models import PromptConfig


def create_image(prompt_cfg: PromptConfig):
    prompt = "Photo realistic white male human in a suit with a tie and a hat."
    prompt_slug = slugify(prompt)

    response = openai.Image.create(
        prompt=prompt,
        n=3,
        size='256x256',
        api_key=os.getenv('OPENAI_API_KEY'),
    )

    print('response:', response['data'])

    for i, item in enumerate(response['data']):
        url = item['url']

        hash_hex = _get_md5_hash(url)
        img_slug = f'{prompt_cfg.ROOT_DIR}/images/{prompt_slug}-{i}-{hash_hex}.jpg'

        img_path = Path(
            prompt_cfg.ROOT_DIR,
            'images',
            f'{prompt_slug}-{i}-{hash_hex}.jpg'
        )
        img_path.parent.mkdir(parents=True, exist_ok=True)

        response = requests.get(url)
        image = Image.open(BytesIO(response.content))
        image.save(f'{img_path}', 'JPEG')

        print('img_slug:', img_slug)
        print('url:', url)


def _get_md5_hash(text):
    hash_object = hashlib.md5()
    hash_object.update(text.encode('utf-8'))
    hash_hex = hash_object.hexdigest()
    return hash_hex
