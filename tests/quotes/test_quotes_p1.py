import pandas as pd
import pytest

from mootdx.quotes import Quotes
from mootdx.quotes import StdQuotes


def make_client(fake_client):
    client = StdQuotes.__new__(StdQuotes)
    client.client = fake_client
    return client


def test_transactions_all_pages_and_sorts():
    class FakeClient:
        def get_history_transaction_data(self, **kwargs):
            if kwargs['start'] == 0:
                return [
                    {'time': '14:58', 'price': 9.31, 'vol': 1, 'buyorsell': 0},
                    {'time': '14:57', 'price': 9.30, 'vol': 2, 'buyorsell': 1},
                ]
            if kwargs['start'] == 2:
                return [{'time': '09:25', 'price': 9.20, 'vol': 3, 'buyorsell': 2}]
            return []

    data = make_client(FakeClient()).transactions_all('000001', date='20170209', page_size=2)

    assert list(data['order']) == [2, 1, 0]
    assert list(data['time']) == ['09:25', '14:57', '14:58']
    assert str(data.index[0]) == '2017-02-09 09:25:00'


def test_transactions_all_raises_at_max_pages():
    class FakeClient:
        def get_history_transaction_data(self, **kwargs):
            return [
                {'time': '14:58', 'price': 9.31, 'vol': 1, 'buyorsell': 0},
                {'time': '14:57', 'price': 9.30, 'vol': 2, 'buyorsell': 1},
            ]

    with pytest.raises(RuntimeError, match='transactions_all reached max_pages'):
        make_client(FakeClient()).transactions_all('000001', date='20170209', page_size=2, max_pages=1)


def test_bars_all_pages_and_formats_once(monkeypatch):
    class FakeClient:
        def __init__(self):
            self.starts = []

        def get_security_bars(self, category, market, code, start, count):
            self.starts.append(start)
            if start == 0:
                return [{'datetime': '2024-01-02', 'close': 1}, {'datetime': '2024-01-01', 'close': 2}]
            if start == 2:
                return [{'datetime': '2023-12-29', 'close': 3}]
            return []

    calls = []

    def fake_to_data(value, **kwargs):
        calls.append(value)
        data = pd.DataFrame(value)
        data.index = pd.to_datetime(data['datetime'])
        return data

    fake = FakeClient()
    monkeypatch.setattr('mootdx.quotes.to_data', fake_to_data)

    data = make_client(fake).bars_all('600036', page_size=2)

    assert fake.starts == [0, 2]
    assert len(calls) == 1
    assert list(data['close']) == [3, 2, 1]


def test_index_bars_all_pages_and_formats_once(monkeypatch):
    class FakeClient:
        def __init__(self):
            self.starts = []

        def get_index_bars(self, category, market, code, start, count):
            self.starts.append(start)
            if start == 0:
                return [{'datetime': '2024-01-02', 'close': 1}, {'datetime': '2024-01-01', 'close': 2}]
            return []

    calls = []

    def fake_to_data(value, **kwargs):
        calls.append(value)
        data = pd.DataFrame(value)
        data.index = pd.to_datetime(data['datetime'])
        return data

    fake = FakeClient()
    monkeypatch.setattr('mootdx.quotes.to_data', fake_to_data)

    data = make_client(fake).index_bars_all('000001', page_size=2)

    assert fake.starts == [0, 2]
    assert len(calls) == 1
    assert list(data['close']) == [2, 1]


def test_quotes_batch_splits_batches():
    class FakeClient:
        def __init__(self):
            self.calls = []

        def get_security_quotes(self, symbols):
            self.calls.append(symbols)
            return [{'market': market, 'code': code, 'price': 1} for market, code in symbols]

    symbols = ['000001'] * 81
    fake = FakeClient()
    data = make_client(fake).quotes_batch(symbols, batch_size=80)

    assert [len(call) for call in fake.calls] == [80, 1]
    assert len(data) == 81


def test_quote_depth_keeps_depth_columns():
    class FakeClient:
        def get_security_quotes(self, symbols):
            item = {'market': 0, 'code': '000001', 'price': 1, 'last_close': 1, 'open': 1, 'high': 1, 'low': 1}
            for index in range(1, 6):
                item[f'bid{index}'] = index
                item[f'ask{index}'] = index + 10
                item[f'bid_vol{index}'] = index + 20
                item[f'ask_vol{index}'] = index + 30
            return [item]

    data = make_client(FakeClient()).quote_depth('000001')

    assert list(data.columns) == [
        'market',
        'code',
        'price',
        'last_close',
        'open',
        'high',
        'low',
        'bid1',
        'ask1',
        'bid_vol1',
        'ask_vol1',
        'bid2',
        'ask2',
        'bid_vol2',
        'ask_vol2',
        'bid3',
        'ask3',
        'bid_vol3',
        'ask_vol3',
        'bid4',
        'ask4',
        'bid_vol4',
        'ask_vol4',
        'bid5',
        'ask5',
        'bid_vol5',
        'ask_vol5',
    ]


def test_p1_online_acceptance():
    client = Quotes.factory(market='std', bestip=True, timeout=5)

    try:
        transactions = client.transactions_all('000001', date='20170209', page_size=800, max_pages=5)
        bars = client.bars_all('600036', frequency=9, page_size=800, max_pages=20)
        symbols = ['000001'] * 81
        quotes = client.quotes_batch(symbols, batch_size=80)
        depth = client.quote_depth(['000001', '600036'])

        assert not transactions.empty
        assert not bars.empty
        assert len(bars) > 10
        assert len(quotes) == 81
        assert {'bid1', 'ask1', 'bid_vol5', 'ask_vol5'}.issubset(depth.columns)
    finally:
        client.close()
