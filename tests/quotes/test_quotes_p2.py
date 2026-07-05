import pandas as pd
import pytest

from mootdx.enhanced import EnhancedQuotesAdapter
from mootdx.quotes import Quotes
from mootdx.quotes import StdQuotes


def make_client(adapter=None, fake_client=None):
    client = StdQuotes.__new__(StdQuotes)
    client.client = fake_client
    if adapter is not None:
        client.enhanced = adapter
    return client


class FakeAdapter:
    def __init__(self):
        self.calls = []

    def minute_extra(self, **kwargs):
        self.calls.append(('minute_extra', kwargs))
        return pd.DataFrame(columns=['market', 'code', 'date'])

    def mini_chart(self, **kwargs):
        self.calls.append(('mini_chart', kwargs))
        return pd.DataFrame(columns=['market', 'code', 'date'])

    def gbbq(self, symbol=None, filepath=None, **kwargs):
        self.calls.append(('gbbq', {'symbol': symbol, 'filepath': filepath, **kwargs}))
        data = pd.DataFrame(
            [
                {
                    'market': 0,
                    'code': '000001',
                    'datetime': 20200101,
                    'date': '2020-01-01',
                    'category': 5,
                    'liutong_before': 80,
                    'total_before': 100,
                    'liutong_after': 90,
                    'total_after': 110,
                },
                {
                    'market': 0,
                    'code': '000001',
                    'datetime': 20210101,
                    'date': '2021-01-01',
                    'category': 5,
                    'liutong_before': 90,
                    'total_before': 110,
                    'liutong_after': 100,
                    'total_after': 120,
                },
            ]
        )
        return data

    def shares_at(self, symbol, date, **kwargs):
        data = self.gbbq(symbol=symbol, **kwargs)
        data = data[data['datetime'] <= int(pd.to_datetime(date).strftime('%Y%m%d'))]
        latest = data.sort_values('datetime').iloc[-1]
        return pd.DataFrame(
            [
                {
                    'code': symbol,
                    'date': str(pd.to_datetime(date).date()),
                    'total_shares': latest['total_after'],
                    'float_shares': latest['liutong_after'],
                }
            ]
        )

    def turnover(self, symbol, date=None, volume=None, **kwargs):
        shares = self.shares_at(symbol, date or '2021-02-01', **kwargs)
        return pd.DataFrame(
            [{'code': symbol, 'volume': volume, 'float_shares': shares.iloc[0]['float_shares'], 'turnover_rate': 10.0}]
        )


def test_minutes_recent_fallback_aggregates_recent_non_empty_days():
    class FakeClient:
        def __init__(self):
            self.dates = []

        def get_history_minute_time_data(self, market, code, date):
            self.dates.append(date)
            if date in {'20240105', '20240103'}:
                return [{'datetime': f'{date} 09:31', 'price': 10, 'vol': 1}]
            return []

    fake = FakeClient()
    data = make_client(fake_client=fake).minutes_recent('000001', days=2, end='2024-01-05', max_search_days=5)

    assert fake.dates == ['20240105', '20240104', '20240103']
    assert list(data['date']) == ['20240103', '20240105']
    assert list(data['code']) == ['000001', '000001']


def test_minute_extra_and_mini_chart_forward_to_adapter():
    adapter = FakeAdapter()
    client = make_client(adapter=adapter)

    assert client.minute_extra('000001', date='20240105').empty
    assert client.mini_chart('000001', date='20240105').empty
    assert [call[0] for call in adapter.calls] == ['minute_extra', 'mini_chart']


def test_adapter_parses_recent_minute_trends_and_mini_chart():
    adapter = EnhancedQuotesAdapter()

    def fake_json(path, params, hosts=None):
        assert path == '/api/qt/stock/trends2/get'
        assert params['ndays'] == 2
        return {
            'data': {
                'trends': [
                    '2024-01-02 09:31,10,10.1,10.2,9.9,1000,10000,10.05',
                    '2024-01-02 09:32,10.1,10.2,10.3,10.0,1100,11000,10.10',
                ]
            }
        }

    adapter._get_json = fake_json

    recent = adapter.minutes_recent('000001', days=2)
    extra = adapter.minute_extra('000001', days=2)
    mini = adapter.mini_chart('000001', days=2, points=1)

    assert list(recent['time']) == ['09:31:00', '09:32:00']
    assert extra.iloc[0]['avg_price'] == 10.05
    assert len(mini) == 1


def test_gbbq_shares_at_and_turnover_forward_to_adapter():
    adapter = FakeAdapter()
    client = make_client(adapter=adapter)

    gbbq = client.gbbq('000001')
    shares = client.shares_at('000001', '2020-12-31')
    turnover = client.turnover('000001', '2021-02-01', volume=10)

    assert len(gbbq) == 2
    assert shares.iloc[0]['total_shares'] == 110
    assert turnover.iloc[0]['turnover_rate'] == 10.0


def test_finance_batch_splits_and_merges():
    class FakeClient:
        def __init__(self):
            self.calls = []

        def get_finance_info(self, market, code):
            self.calls.append(code)
            if code == 'bad':
                return {}
            return {'market': market, 'liutongguben': 100}

    fake = FakeClient()
    data = make_client(fake_client=fake).finance_batch(['000001', '600036', 'bad'], batch_size=1)

    assert fake.calls == ['000001', '600036', 'bad']
    assert data['code'].tolist() == ['000001', '600036']
    assert len(data) == 2


@pytest.mark.online
def test_p2_quotes_online_acceptance():
    client = Quotes.factory(market='std', bestip=True, timeout=5)

    try:
        minutes = client.minutes_recent('000001', days=2)
        gbbq = client.gbbq('000001')
        finance = client.finance_batch(['000001', '600036'])

        assert isinstance(minutes, pd.DataFrame)
        assert isinstance(gbbq, pd.DataFrame)
        assert isinstance(finance, pd.DataFrame)
        assert not finance.empty
    finally:
        client.close()
