from os import path
from json import load
import typing
import os

SOCIAL_MAPS = {
    'facebook': {
        'login_url': 'https://facebook.com/login',
        'filename': 'facebook.json'
    },
    'reddit': {
        'login_url': 'https://reddit.com/login',
        'filename': 'reddit.json'
    },
    'instagram': {
        'login_url': 'https://instagram.com/accounts/login',
        'filename': 'instagram.json'
    }
}

# Browser configuration
BROWSER_CONFIG = {
    'use_local_chrome': True,  # Set to False to use Chromium
    'chrome_path': '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    'chrome_args': [
        '--start-maximized',
        '--no-first-run',
        '--disable-blink-features=AutomationControlled',
        '--disable-web-security',
        '--disable-features=VizDisplayCompositor'
    ]
}

PROJECT_ROOT = path.dirname(path.abspath(__name__))

def get_sources_list() -> typing.List:
    with open(f'{PROJECT_ROOT}/groups.json', 'r') as sources_file:
        return load(sources_file)
