import asyncio
import copy
import functools
import json
import socket
import time

from tdxpy.constants import hq_hosts
from tdxpy.exhq import TdxExHq_API
from tdxpy.hq import TdxHq_API

from mootdx.consts import CONFIG
from mootdx.consts import EX_HOSTS
from mootdx.consts import GP_HOSTS
from mootdx.consts import HQ_HOSTS
from mootdx.logger import logger
from mootdx.utils import get_config_path

hosts = {
    'HQ': [{'addr': hs[1], 'port': hs[2], 'time': 0, 'site': hs[0]} for hs in hq_hosts + HQ_HOSTS],
    'EX': [{'addr': hs[1], 'port': hs[2], 'time': 0, 'site': hs[0]} for hs in EX_HOSTS],
    'GP': [{'addr': hs[1], 'port': hs[2], 'time': 0, 'site': hs[0]} for hs in GP_HOSTS],
}

results = {k: [] for k in hosts}


def connect(proxy: dict) -> dict:
    """
    连接服务器函数

    :param proxy: 代理IP信息
    :return:
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(.7)

        start = time.perf_counter()

        sock.connect((proxy.get('addr'), int(proxy.get('port'))))
        sock.close()

        proxy['time'] = (time.perf_counter() - start) * 1000

        logger.debug('{addr}:{port} 验证通过，响应时间：{time} ms.'.format(**proxy))
    except socket.timeout as ex:  # noqa
        logger.debug('{addr},{port} time out.'.format(**proxy))
        proxy['time'] = None
    except ConnectionRefusedError as ex:  # noqa
        logger.debug('{addr},{port} 验证失败.'.format(**proxy))
        proxy['time'] = None

    return proxy


def connect2(proxy, index='HQ'):
    if index == 'GP':
        return connect(proxy)

    api = (TdxHq_API(), TdxExHq_API())[index != 'HQ']
    fun = ('get_security_count', 'get_instrument_count')[index != 'HQ']

    proxy['time'] = None

    try:
        with api.connect(proxy.get('addr'), int(proxy.get('port')), time_out=0.7):
            tms = time.perf_counter()
            if getattr(api, fun)():
                proxy['time'] = (time.perf_counter() - tms) * 1000
                logger.debug('{addr}:{port} 验证通过，响应时间：{time} ms.'.format(**proxy))
            else:
                logger.debug('{addr}:{port} 验证失败.'.format(**proxy))
    except socket.timeout:  # noqa
        logger.debug('{addr}:{port} time out.'.format(**proxy))
        proxy['time'] = None
    except Exception:  # noqa
        logger.debug('{addr}:{port} 验证失败.'.format(**proxy))

    return proxy


async def verify(proxy: dict, index):
    """
    检验代理连通性函数

    :param index:
    :param proxy: 代理IP信息
    :return:
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, functools.partial(connect2, proxy=proxy, index=index))


def server(index=None, limit=5, console=False, sync=True):
    _hosts = [dict(item) for item in hosts[index]]

    async def async_event():
        tasks = [verify(proxy, index) for proxy in _hosts]
        return await asyncio.gather(*tasks)

    data = [connect2(proxy, index) for proxy in _hosts] if sync else asyncio.run(async_event())
    servers = [item for item in data if item.get('time')]
    servers.sort(key=lambda item: item['time'])

    if limit:
        servers = servers[:limit]

    results[index] = servers

    # 结果按响应时间从小到大排序
    if console:
        from prettytable import PrettyTable

        logger.debug('[√] 最优服务器:')

        t = PrettyTable(['Name', 'Addr', 'Port', 'Time'])
        t.align['Name'] = 'l'
        t.align['Addr'] = 'l'
        t.align['Port'] = 'l'
        t.align['Time'] = 'r'
        t.padding_width = 1

        for host in servers:
            t.add_row(
                [
                    host['site'],
                    host['addr'],
                    host['port'],
                    '{:5.2f} ms'.format(host['time']),
                ]
            )

        logger.debug('\n' + str(t))

    return [(item['addr'], int(item['port'])) for item in servers]


def check_server(console=False, limit=5, sync=False) -> None:
    return bestip(console=console, limit=limit, sync=sync)


def bestip(console=False, limit=5, sync=False) -> None:
    config_ = get_config_path('config.json')
    default = copy.deepcopy(CONFIG)

    logger.info('[-] 选择最快的服务器...')
    logger.debug(f'sync => {sync}')

    for index in ['HQ', 'EX', 'GP']:
        try:
            data = server(index=index, limit=limit, console=console, sync=sync)

            if data:
                default['BESTIP'][index] = data[0]
        except RuntimeError:
            logger.error('请手动运行`python -m mootdx bestip`')
            break

    json.dump(default, open(config_, 'w', encoding='utf-8'), indent=2, ensure_ascii=False)


if __name__ == '__main__':
    bestip(sync=False, limit=5, console=True)
