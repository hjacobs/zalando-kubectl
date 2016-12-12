import os
import subprocess
import sys

import click
import requests
import stups_cli.config
import zign.api
from clickclick import Action, error

from . import kube_config

APP_NAME = 'zalando-kubectl'
KUBECTL_URL_TEMPLATE = 'https://storage.googleapis.com/kubernetes-release/release/{version}/bin/{os}/{arch}/kubectl'
KUBECTL_VERSION = 'v1.4.7'


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


def fix_url(url):
    # strip potential whitespace from prompt
    url = url.strip()
    if not url.startswith('http'):
        # user convenience
        url = 'https://' + url
    return url


def proxy():
    kubectl = ensure_kubectl()

    subprocess.call([kubectl] + sys.argv[1:])


def get_api_server_url(cluster_registry_url: str, cluster_id: str):
    token = zign.api.get_token('kubectl', ['uid'])
    response = requests.get('{}/kubernetes-clusters/{}'.format(cluster_registry_url, cluster_id),
                            headers={'Authorization': 'Bearer {}'.format(token)}, timeout=5)
    if response.status_code == 404:
        error('Kubernetes cluster {} not found in Cluster Registry'.format(cluster_id))
        exit(1)
    response.raise_for_status()
    data = response.json()
    url = data.get('api_server_url')
    return url


def login(args: list):
    config = stups_cli.config.load_config(APP_NAME)

    if args:
        cluster_or_url = args[0]
    else:
        cluster_or_url = click.prompt('Cluster ID or URL of Kubernetes API server')

    if len(cluster_or_url.split(':')) >= 3:
        # looks like a Cluster ID (aws:123456789012:eu-central-1:kube-1)
        cluster_id = cluster_or_url
        cluster_registry = config.get('cluster_registry')
        if not cluster_registry:
            cluster_registry = fix_url(click.prompt('URL of Cluster Registry'))
        url = get_api_server_url(cluster_registry, cluster_id)
    else:
        url = cluster_or_url

    url = fix_url(url)

    config['api_server'] = url
    stups_cli.config.store_config(config, APP_NAME)
    return url


def configure(args):
    # naive option parsing
    config = {'cluster_registry': None}
    for arg in args:
        # TODO: proper error handling
        if arg.startswith('--'):
            key, val = arg.split('=', 1)
            config_key = key[2:].replace('-', '_')
            if config_key not in config:
                error('Unsupported option "{}"'.format(key))
                exit(2)
            config[config_key] = val
    stups_cli.config.store_config(config, APP_NAME)


def main(args=None):
    try:
        if not args:
            args = sys.argv
        cmd = ''.join(args[1:2])
        cmd_args = args[2:]
        if cmd == 'login':
            kube_config.update(login(cmd_args))
        elif cmd == 'configure':
            configure(cmd_args)
        else:
            kube_config.update(get_url())
            proxy()
    except KeyboardInterrupt:
        pass
