import pandas as pd
import pytest

from mootdx.offline import append_daily
from mootdx.offline import append_minute
from mootdx.offline import write_daily
from mootdx.offline import write_minute
from mootdx.reader import Reader


def test_write_daily_reads_back_with_reader(tmp_path):
    filepath = tmp_path / 'vipdoc' / 'sz' / 'lday' / 'sz000001.day'
    data = pd.DataFrame(
        {
            'date': ['2024-01-02', '2024-01-03'],
            'open': [10.0, 11.0],
            'high': [10.5, 11.5],
            'low': [9.5, 10.5],
            'close': [10.2, 11.2],
            'amount': [100000.0, 200000.0],
            'volume': [1000.0, 2000.0],
        }
    )

    assert write_daily(filepath, data, append=False) == 2
    assert append_daily(filepath, data) == 0

    result = Reader.factory('std', tdxdir=str(tmp_path)).daily('000001')

    assert len(result) == 2
    assert list(result['close']) == pytest.approx([10.2, 11.2])
    assert list(result['volume']) == [1000.0, 2000.0]


def test_append_daily_only_writes_new_dates(tmp_path):
    filepath = tmp_path / 'vipdoc' / 'sz' / 'lday' / 'sz000001.day'
    first = pd.DataFrame(
        {
            'date': ['2024-01-02'],
            'open': [10],
            'high': [11],
            'low': [9],
            'close': [10],
            'amount': [100],
            'volume': [1000],
        }
    )
    second = pd.DataFrame(
        {
            'date': ['2024-01-02', '2024-01-03'],
            'open': [10, 12],
            'high': [11, 13],
            'low': [9, 11],
            'close': [10, 12],
            'amount': [100, 200],
            'volume': [1000, 2000],
        }
    )

    assert write_daily(filepath, first, append=False) == 1
    assert append_daily(filepath, second) == 1

    result = Reader.factory('std', tdxdir=str(tmp_path)).daily('000001')
    assert len(result) == 2
    assert list(result.index.strftime('%Y-%m-%d')) == ['2024-01-02', '2024-01-03']


def test_write_lc1_and_lc5_minutes_read_back_with_reader(tmp_path):
    data = pd.DataFrame(
        {
            'datetime': ['2024-01-02 09:31:00', '2024-01-02 09:32:00'],
            'open': [10.0, 10.1],
            'high': [10.2, 10.3],
            'low': [9.9, 10.0],
            'close': [10.1, 10.2],
            'amount': [10000.0, 11000.0],
            'volume': [1000, 1100],
        }
    )
    lc1 = tmp_path / 'vipdoc' / 'sz' / 'minline' / 'sz000001.lc1'
    lc5 = tmp_path / 'vipdoc' / 'sz' / 'fzline' / 'sz000001.lc5'

    assert write_minute(lc1, data, kind='lc1', append=False) == 2
    assert append_minute(lc1, data, kind='lc1') == 0
    assert write_minute(lc5, data, kind='lc5', append=False) == 2

    reader = Reader.factory('std', tdxdir=str(tmp_path))
    one_min = reader.minute('000001', suffix=1)
    five_min = reader.minute('000001', suffix=5)

    assert len(one_min) == 2
    assert len(five_min) == 2
    assert list(one_min['close'].round(2)) == [10.1, 10.2]
    assert list(five_min.index.strftime('%H:%M:%S')) == ['09:31:00', '09:32:00']
