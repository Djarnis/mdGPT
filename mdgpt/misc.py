import os
import openai
from operator import itemgetter
from rich import print


def list_engines():
    print('Listing engines ...')
    if os.getenv('OPENAI_API_KEY') is None:
        print('Please set OPENAI_API_KEY environment variable.')
        exit(1)

    response = openai.Engine.list(api_key=os.getenv('OPENAI_API_KEY'))
    for eng in sorted(response['data'], key=itemgetter('owner', 'id')):
        print(f"{eng['owner']}:", eng['id'])
