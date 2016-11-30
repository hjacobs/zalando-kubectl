import os
import subprocess
import sys

import click
import requests
import stups_cli.config
import zign.api
from clickclick import Action

from . import kube_config

APP_NAME = 'zalando-kubectl'
KUBECTL_URL_TEMPLATE = 'https://storage.googleapis.com/kubernetes-release/release/{version}/bin/{os}/{arch}/kubectl'
KUBECTL_VERSION = 'v1.4.6'


def ensure_kubectl():
    kubectl = os.path.join(click.get_app_dir(APP_NAME), 'kubectl-{}'.format(KUBECTL_VERSION))

    if not os.path.exists(kubectl):
        os.makedirs(os.path.dirname(kubectl), exist_ok=True)

        platform = sys.platform  # linux or darwin
        arch = 'amd64'  # FIXME: hardcoded value
        url = KUBECTL_URL_TEMPLATE.format(version=KUBECTL_VERSION, os=platform, arch=arch)
        with Action('Downloading {}..'.format(url)) as act:
            response = requests.get(url, stream=True)
            local_file = kubectl + '.download'
            with open(local_file, 'wb') as fd:
                for i, chunk in enumerate(response.iter_content(chunk_size=4096)):
                    if chunk:  # filter out keep-alive new chunks
                        fd.write(chunk)
                        if i % 256 == 0:  # every 1MB
                            act.progress()
            os.chmod(local_file, 0o755)
            os.rename(local_file, kubectl)

    return kubectl


def get_url():
    while True:
        try:
            config = stups_cli.config.load_config(APP_NAME)
            return config['api_server']
        except:
            login([])


def proxy():
    url = get_url()
    kubectl = ensure_kubectl()

    token = zign.api.get_token('kubectl', ['uid'])
    kube_config.update(url, token)
    subprocess.call([kubectl] + sys.argv[1:])


def login(args):
    if args:
        url = args[0]
    else:
        url = click.prompt('URL of Kubernetes API server')

    if not url.startswith('http'):
        # user convenience
        url = 'https://' + url

    config = stups_cli.config.load_config(APP_NAME)
    config['api_server'] = url
    stups_cli.config.store_config(config, APP_NAME)


def configure(args):
    # naive option parsing
    config = {}
    for arg in args:
        if arg.startswith('--'):
            key, val = arg.split('=', 1)
            config[key[2:].replace('-', '_')] = val
    stups_cli.config.store_config(config, APP_NAME)


def main(args=None):
    try:
        if not args:
            args = sys.argv
        cmd = ''.join(args[1:2])
        cmd_args = args[2:]
        if cmd == 'login':
            login(cmd_args)
        elif cmd == 'configure':
            configure(cmd_args)
        else:
            proxy()
    except KeyboardInterrupt:
        pass
