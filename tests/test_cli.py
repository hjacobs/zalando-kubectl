
from unittest.mock import MagicMock

from zalando_kubectl.main import main

def test_main(monkeypatch):
    call = MagicMock()
    monkeypatch.setattr('zalando_kubectl.main.ensure_kubectl', MagicMock())
    monkeypatch.setattr('zalando_kubectl.main.login', MagicMock())
    monkeypatch.setattr('subprocess.call', call)
    monkeypatch.setattr('zalando_kubectl.main.get_url', MagicMock(return_value='foo,example.org'))

    main(['foo', 'get', 'pods'])
