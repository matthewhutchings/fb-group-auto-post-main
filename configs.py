from os import path
from json import load
import typing

SOCIAL_MAPS = {
    'facebook': {
        'login_url': 'https://facebook.com/login',
        'filename': 'facebook.json'
    },
    'reddit': {
        'login_url': 'https://www.reddit.com/login',
        'filename': 'reddit.json'
    },
    'instagram': {
        'login_url': 'https://www.instagram.com/accounts/login/',
        'filename': 'instagram.json'
    }
}

PROJECT_ROOT = path.dirname(path.abspath(__name__))

def get_sources_list() -> typing.List:
    with open(f'{PROJECT_ROOT}/groups.json', 'r') as sources_file:
        return load(sources_file)
