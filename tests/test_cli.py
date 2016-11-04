
from unittest.mock import MagicMock
from zalando_kubectl.main import main
from zalando_kubectl.kube_config import kube_config


def test_main(monkeypatch):
    call = MagicMock()
    monkeypatch.setattr('zalando_kubectl.main.ensure_kubectl', MagicMock())
    monkeypatch.setattr('zalando_kubectl.main.login', MagicMock())
    monkeypatch.setattr('subprocess.call', call)
    monkeypatch.setattr('zalando_kubectl.main.get_url', MagicMock(return_value='foo,example.org'))
    monkeypatch.setattr('zign.api.get_token', MagicMock(return_value='mytok'))
    monkeypatch.setattr('zalando_kubectl.kube_config.kube_config.update', MagicMock(return_value={}))
    main(['foo', 'get', 'pods'])


def test_kube_config(monkeypatch):
    monkeypatch.setattr('zalando_kubectl.kube_config.kube_config.write_config', MagicMock())
    monkeypatch.setattr('zalando_kubectl.kube_config.kube_config.read_config', MagicMock(return_value={}))

    cnfg = kube_config.update('zalan.k8s.do', 'token')
    assert cnfg['current-context'] == 'zalan_k8s_do'
    assert cnfg['apiVersion'] == 'v1'
    assert cnfg['kind'] == 'Config'
    assert len([clst for clst in cnfg['clusters'] if clst['name'] == 'zalan_k8s_do']) > 0
    assert len([ctx for ctx in cnfg['contexts'] if ctx['name'] == 'zalan_k8s_do']) > 0
    assert len([usr for usr in cnfg['users'] if usr['name'] == 'zalan_k8s_do']) > 0

    monkeypatch.setattr(
                        'zalando_kubectl.kube_config.kube_config.read_config',
                        MagicMock(return_value={'clusters': [{'name': 'foo'}]}))
    cnfg = kube_config.update('zalan.k8s.do', 'token')
    assert len([cnfg['clusters']]) > 0

    monkeypatch.setattr(
                        'zalando_kubectl.kube_config.kube_config.read_config',
                        MagicMock(return_value={'clusters': [{'name': 'zalan_k8s_do'}]}))
    cnfg = kube_config.update('zalan.k8s.do', 'token')
    assert len([cnfg['clusters']]) == 1
