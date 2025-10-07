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
    'use_cdp_connection': True,  # Connect to existing Chrome via CDP
    'cdp_port': 9222,  # Chrome remote debugging port
    'chrome_path': '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    'chrome_args': [
        '--start-maximized',
        '--no-first-run',
        '--disable-blink-features=AutomationControlled',
        '--disable-web-security',
        '--disable-features=VizDisplayCompositor',
        '--remote-debugging-port=9222',  # Enable remote debugging
        '--remote-allow-origins=*'  # Allow connections from any origin
    ]
}

PROJECT_ROOT = path.dirname(path.abspath(__name__))

def get_sources_list() -> typing.List:
    with open(f'{PROJECT_ROOT}/groups.json', 'r') as sources_file:
        return load(sources_file)
