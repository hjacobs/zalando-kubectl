import os
import subprocess
import sys

import click
import requests
import stups_cli.config
import time
import zign.api
from clickclick import Action, error, info

from . import kube_config

APP_NAME = 'zalando-kubectl'
KUBECTL_URL_TEMPLATE = 'https://storage.googleapis.com/kubernetes-release/release/{version}/bin/{os}/{arch}/kubectl'
KUBECTL_VERSION = 'v1.5.2'


def ensure_kubectl():
    kubectl = os.path.join(click.get_app_dir(APP_NAME), 'kubectl-{}'.format(KUBECTL_VERSION))

    if not os.path.exists(kubectl):
        os.makedirs(os.path.dirname(kubectl), exist_ok=True)

        platform = sys.platform  # linux or darwin
        arch = 'amd64'  # FIXME: hardcoded value
        url = KUBECTL_URL_TEMPLATE.format(version=KUBECTL_VERSION, os=platform, arch=arch)
        with Action('Downloading {} to {}..'.format(url, kubectl)) as act:
            response = requests.get(url, stream=True)
            response.raise_for_status()
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


def proxy(args=None):
    kubectl = ensure_kubectl()

    if not args:
        args = sys.argv[1:]

    subprocess.call([kubectl] + args)


def get_api_server_url_for_cluster_id(cluster_registry_url: str, cluster_id: str):
    token = zign.api.get_token('kubectl', ['uid'])
    response = requests.get('{}/kubernetes-clusters/{}'.format(cluster_registry_url, cluster_id),
                            headers={'Authorization': 'Bearer {}'.format(token)}, timeout=10)
    if response.status_code == 404:
        error('Kubernetes cluster {} not found in Cluster Registry'.format(cluster_id))
        exit(1)
    response.raise_for_status()
    data = response.json()
    url = data.get('api_server_url')
    return url


def get_api_server_url_for_alias(cluster_registry_url: str, alias: str):
    token = zign.api.get_token('kubectl', ['uid'])
    response = requests.get('{}/kubernetes-clusters'.format(cluster_registry_url),
                            params={'alias': alias},
                            headers={'Authorization': 'Bearer {}'.format(token)}, timeout=10)
    response.raise_for_status()
    data = response.json()
    for cluster in data['items']:
        return cluster['api_server_url']
    # try to use alias as URL
    return alias


def looks_like_url(alias_or_url: str):
    if alias_or_url.startswith('http:') or alias_or_url.startswith('https:'):
        # https://something
        return True
    elif len(alias_or_url.split('.')) > 2:
        # foo.example.org
        return True
    return False


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
        url = get_api_server_url_for_cluster_id(cluster_registry, cluster_id)
    elif looks_like_url(cluster_or_url):
        url = cluster_or_url
    else:
        alias = cluster_or_url
        cluster_registry = config.get('cluster_registry')
        if not cluster_registry:
            cluster_registry = fix_url(click.prompt('URL of Cluster Registry'))
        url = get_api_server_url_for_alias(cluster_registry, alias)

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


def _open_dashboard_in_browser():
    import webbrowser
    # sleep some time to make sure "kubectl proxy" runs
    url = 'http://localhost:8001/api/v1/namespaces/kube-system/services/kubernetes-dashboard/proxy'
    with Action('Waiting for local kubectl proxy..') as act:
        for i in range(20):
            time.sleep(0.1)
            try:
                requests.get(url, timeout=2)
            except:
                act.progress()
            else:
                break
    info('\nOpening {} ..'.format(url))
    webbrowser.open(url)


def dashboard(args):
    import threading
    # first make sure kubectl was downloaded
    ensure_kubectl()
    thread = threading.Thread(target=_open_dashboard_in_browser)
    # start short-lived background thread to allow running "kubectl proxy" in main thread
    thread.start()
    kube_config.update(get_url())
    proxy(['proxy'])


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
        elif cmd == 'dashboard':
            dashboard(cmd_args)
        else:
            kube_config.update(get_url())
            proxy()
    except KeyboardInterrupt:
        pass
