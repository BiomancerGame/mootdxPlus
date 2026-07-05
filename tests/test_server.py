import json
import shutil
from importlib import import_module
from pathlib import Path

server_module = import_module('mootdx.server')


def test_server_uses_host_copy_and_limits(monkeypatch):
    monkeypatch.setitem(server_module.hosts, 'HQ', [
        {'addr': 'slow', 'port': 7709, 'time': 0, 'site': 'slow'},
        {'addr': 'fast', 'port': 7709, 'time': 0, 'site': 'fast'},
        {'addr': 'bad', 'port': 7709, 'time': 0, 'site': 'bad'},
    ])

    def fake_connect2(proxy, index='HQ'):
        times = {'slow': 3, 'fast': 1, 'bad': None}
        proxy['time'] = times[proxy['addr']]
        return proxy

    monkeypatch.setattr(server_module, 'connect2', fake_connect2)

    result = server_module.server(index='HQ', limit=1, sync=True)

    assert result == [('fast', 7709)]
    assert [item['addr'] for item in server_module.hosts['HQ']] == ['slow', 'fast', 'bad']


def test_server_async_probe(monkeypatch):
    monkeypatch.setitem(server_module.hosts, 'HQ', [
        {'addr': 'one', 'port': 7709, 'time': 0, 'site': 'one'},
        {'addr': 'two', 'port': 7709, 'time': 0, 'site': 'two'},
    ])

    def fake_connect2(proxy, index='HQ'):
        proxy['time'] = {'one': 2, 'two': 1}[proxy['addr']]
        return proxy

    monkeypatch.setattr(server_module, 'connect2', fake_connect2)

    assert server_module.server(index='HQ', sync=False) == [('two', 7709), ('one', 7709)]


def test_bestip_writes_config_without_mutating_defaults(monkeypatch):
    config_home = Path(__file__).resolve().parents[1] / '.mootdx-test'
    shutil.rmtree(config_home, ignore_errors=True)
    monkeypatch.setenv('MOOTDX_HOME', str(config_home))

    def fake_server(index=None, limit=5, console=False, sync=True):
        return [(f'{index.lower()}-host', 7709)]

    monkeypatch.setattr(server_module, 'server', fake_server)

    server_module.bestip(sync=True)

    try:
        config = json.loads((config_home / 'config.json').read_text(encoding='utf-8'))
        assert config['BESTIP']['HQ'] == ['hq-host', 7709]
        assert server_module.CONFIG['BESTIP']['HQ'] == ''
    finally:
        shutil.rmtree(config_home, ignore_errors=True)
