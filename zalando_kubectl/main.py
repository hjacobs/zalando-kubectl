import click
import os
import requests
import subprocess
import sys
import yaml
import zign.api

from clickclick import Action

APP_NAME = 'zalando-kubectl'
KUBECTL_URL_TEMPLATE = 'https://storage.googleapis.com/kubernetes-release/release/{version}/bin/{os}/{arch}/kubectl'
KUBECTL_VERSION = 'v1.4.4'


def get_config_path():
    return os.path.join(click.get_app_dir(APP_NAME), 'config.yaml')


def ensure_kubectl():
    kubectl = os.path.join(click.get_app_dir(APP_NAME), 'kubectl')

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
            with open(get_config_path()) as fd:
                data = yaml.safe_load(fd)
            return data['url']
        except:
            login([])


def proxy():
    url = get_url()
    kubectl = ensure_kubectl()

    token = zign.api.get_token('kubectl', ['uid'])

    path = os.path.expanduser('~/.kube/config')
    os.makedirs(os.path.dirname(path), exist_ok=True)

    # TODO: we should not overwrite the whole kubeconfig
    config = {
        'apiVersion': 'v1',
        'kind': 'Config',
        'clusters': [{'name': 'default', 'cluster': {'server': url}}],
        'users': [{'name': 'default', 'user': {'token': token}}],
        'contexts': [{'name': 'default', 'context': {'cluster': 'default', 'user': 'default'}}],
        'current-context': 'default'
    }

    with open(path, 'w') as fd:
        yaml.safe_dump(config, fd)

    subprocess.call([kubectl] + sys.argv[1:])


def login(args):
    if args:
        url = args[0]
    else:
        url = click.prompt('URL of Kubernetes API server')

    if not url.startswith('http'):
        # user convenience
        url = 'https://' + url

    path = get_config_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as fd:
        yaml.safe_dump({'url': url}, fd)


def main(args=None):
    if not args:
        args = sys.argv
    cmd = ''.join(args[1:2])
    cmd_args = args[2:]
    if cmd == 'login':
        login(cmd_args)
    else:
        proxy()
