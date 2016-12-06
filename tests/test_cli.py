from unittest.mock import MagicMock

import pytest
import zalando_kubectl.main
from zalando_kubectl import kube_config
from zalando_kubectl.main import main


def test_main(monkeypatch):
    call = MagicMock()
    monkeypatch.setattr('zalando_kubectl.main.ensure_kubectl', MagicMock())
    monkeypatch.setattr('zalando_kubectl.main.login', MagicMock())
    monkeypatch.setattr('subprocess.call', call)
    monkeypatch.setattr('zalando_kubectl.main.get_url', MagicMock(return_value='foo,example.org'))
    monkeypatch.setattr('zign.api.get_token', MagicMock(return_value='mytok'))
    monkeypatch.setattr('zalando_kubectl.kube_config.update', MagicMock(return_value={}))
    main(['foo', 'get', 'pods'])


def test_kube_config(monkeypatch):
    monkeypatch.setattr('zalando_kubectl.kube_config.write_config', MagicMock())
    monkeypatch.setattr('zalando_kubectl.kube_config.read_config', MagicMock(return_value={}))
    monkeypatch.setattr('zign.api.get_token', MagicMock(return_value='mytok'))
    cnfg = kube_config.update('zalan.k8s.do')
    assert cnfg['current-context'] == 'zalan_k8s_do'
    assert cnfg['apiVersion'] == 'v1'
    assert cnfg['kind'] == 'Config'
    assert len([clst for clst in cnfg['clusters'] if clst['name'] == 'zalan_k8s_do']) > 0
    assert len([ctx for ctx in cnfg['contexts'] if ctx['name'] == 'zalan_k8s_do']) > 0
    assert len([usr for usr in cnfg['users'] if usr['name'] == 'zalan_k8s_do']) > 0

    monkeypatch.setattr(
                        'zalando_kubectl.kube_config.read_config',
                        MagicMock(return_value={'clusters': [{'name': 'foo'}]}))
    cnfg = kube_config.update('zalan.k8s.do')
    assert len([cnfg['clusters']]) > 0

    monkeypatch.setattr(
                        'zalando_kubectl.kube_config.read_config',
                        MagicMock(return_value={'clusters': [{'name': 'zalan_k8s_do'}]}))
    cnfg = kube_config.update('zalan.k8s.do')
    assert len([cnfg['clusters']]) == 1


def test_login(monkeypatch):
    cluster_registry = 'https://cluster-registry.example.org'

    store_config = MagicMock()
    monkeypatch.setattr('stups_cli.config.load_config', lambda x: {'cluster_registry': cluster_registry})
    monkeypatch.setattr('stups_cli.config.store_config', store_config)

    api_url = 'https://my-cluster.example.org'

    def get_api_server_url(cluster_registry_url, cluster_id):
        assert cluster_registry_url == cluster_registry
        assert cluster_id == 'aws:123:eu-west-1:my-kube-1'
        return api_url

    monkeypatch.setattr('zalando_kubectl.main.get_api_server_url', get_api_server_url)

    url = zalando_kubectl.main.login(['aws:123:eu-west-1:my-kube-1'])
    assert api_url == url


def test_get_api_server_url(monkeypatch):
    get = MagicMock()
    get.return_value.json.return_value = {'api_server_url': 'https://my-cluster.example.org'}

    monkeypatch.setattr('zign.api.get_token', lambda x, y: 'mytok')
    monkeypatch.setattr('requests.get', get)

    url = zalando_kubectl.main.get_api_server_url('https://cluster-registry.example.org', 'my-cluster-id')
    assert url == 'https://my-cluster.example.org'


def test_configure(monkeypatch):
    config = {}

    def store_config(conf, _):
        config.update(**conf)
    monkeypatch.setattr('stups_cli.config.store_config', store_config)
    with pytest.raises(SystemExit):
        zalando_kubectl.main.configure(['--my-option=123'])
    zalando_kubectl.main.configure(['--cluster-registry=123'])
    assert {'cluster_registry': '123'} == config
