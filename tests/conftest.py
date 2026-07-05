import os
from pathlib import Path

import pandas
import pytest

os.environ.setdefault('MOOTDX_HOME', str(Path(__file__).resolve().parents[1] / '.mootdx'))

from mootdx.quotes import Quotes


def pytest_configure(config):
    config.addinivalue_line('markers', 'online: requires live network access to TDX or financial data servers')


def pytest_collection_modifyitems(config, items):
    if os.environ.get('MOOTDX_RUN_ONLINE') == '1':
        return

    skip_online = pytest.mark.skip(reason='set MOOTDX_RUN_ONLINE=1 to run online tests')
    for item in items:
        if 'online' in item.keywords:
            item.add_marker(skip_online)


def is_empty(obj):
    if isinstance(obj, pandas.DataFrame):
        return obj.empty

    return not obj


@pytest.fixture()
def quotes():
    return Quotes.factory('std')

# @pytest.fixture()
# def reader():
#     return Reader.factory("std")
