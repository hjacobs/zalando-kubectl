import os
import zign.api
import yaml

KUBECONFIG = os.path.expanduser('~/.kube/config')


def update(url):
    token = zign.api.get_token('kubectl', ['uid'])
    name = generate_name(url)
    new_config = {
        'apiVersion': 'v1',
        'kind': 'Config',
        'clusters': [{'name': name, 'cluster': {'server': url}}],
        'users': [{'name': name, 'user': {'token': token}}],
        'contexts': [{'name': name, 'context': {'cluster': name, 'user': name}}],
        'current-context': name
    }
    config = insert(new_config)
    write_config(config)
    return config


def write_config(config):
    os.makedirs(os.path.dirname(KUBECONFIG), exist_ok=True)
    with open(KUBECONFIG, 'w') as fd:
        yaml.safe_dump(config, fd)


def generate_name(url):
    url = url.replace('http://', '')
    url = url.replace('https://', '')
    url = url.replace('.', '_')
    url = url.replace('/', '')
    return url


def read_config():
    try:
        with open(KUBECONFIG, 'r') as fd:
            data = yaml.safe_load(fd)
        if isinstance(data, dict):
            return data
    except:
        pass
    return {}


def insert(new_config):
    config = read_config()
    config['current-context'] = new_config['current-context']
    config['apiVersion'] = new_config['apiVersion']
    config['kind'] = new_config['kind']
    for key in ['clusters', 'users', 'contexts']:
        for item in new_config[key]:
            insert_key(config, item, key)
    return config


def insert_key(config, item, key):
    if key not in config:
        config[key] = [item]
        return
    for it in config[key]:
        if it['name'] == item['name']:
            it.update(**item)
            return
    config[key].append(item)
