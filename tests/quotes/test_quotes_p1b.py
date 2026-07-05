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

    def _record(self, name, **kwargs):
        self.calls.append((name, kwargs))
        return pd.DataFrame([{'method': name, **kwargs}])

    def auction(self, **kwargs):
        return self._record('auction', **kwargs)

    def capital_flow(self, **kwargs):
        return self._record('capital_flow', **kwargs)

    def fund_flow(self, **kwargs):
        return self._record('fund_flow', **kwargs)

    def boards(self, **kwargs):
        return self._record('boards', **kwargs)

    def board_members(self, **kwargs):
        return self._record('board_members', **kwargs)

    def belong_boards(self, **kwargs):
        return self._record('belong_boards', **kwargs)

    def board_summary(self, **kwargs):
        return self._record('board_summary', **kwargs)

    def board_ranking(self, **kwargs):
        return self._record('board_ranking', **kwargs)

    def symbol_info(self, **kwargs):
        return self._record('symbol_info', **kwargs)

    def price_limits(self, **kwargs):
        return self._record('price_limits', **kwargs)


def test_stdquotes_p1b_methods_forward_to_adapter():
    adapter = FakeAdapter()
    client = make_client(adapter=adapter)

    assert client.auction('000001').iloc[0]['symbol'] == '000001'
    assert client.capital_flow('000001').iloc[0]['symbol'] == '000001'
    assert client.fund_flow('000001', start='20260701', end='20260703').iloc[0]['start'] == '20260701'
    assert client.boards(type='GN').iloc[0]['type'] == 'GN'
    assert client.board_members('BK0475').iloc[0]['code'] == 'BK0475'
    assert client.belong_boards('000001').iloc[0]['symbol'] == '000001'
    assert bool(client.board_summary('BK0475', members=True).iloc[0]['members'])
    assert client.board_ranking(type='HY', sort_by='amount', top=2).iloc[0]['top'] == 2
    assert client.symbol_info('000001').iloc[0]['symbol'] == '000001'
    assert client.price_limits('000001', date='20260703').iloc[0]['date'] == '20260703'

    assert [call[0] for call in adapter.calls] == [
        'auction',
        'capital_flow',
        'fund_flow',
        'boards',
        'board_members',
        'belong_boards',
        'board_summary',
        'board_ranking',
        'symbol_info',
        'price_limits',
    ]


def test_market_stat_uses_tdx_statistics_indexes():
    class FakeClient:
        def get_security_quotes(self, symbols):
            assert [item[1] for item in symbols] == ['880005', '880001', '880006']
            return [
                {'code': '880005', 'price': 123.4, 'open': 45.6, 'low': 7.8, 'high': 200, 'amount': 9, 'vol': 10},
                {'code': '880001', 'price': 88.8},
                {'code': '880006', 'price': 12.3, 'open': 4.5},
            ]

    data = make_client(fake_client=FakeClient()).market_stat()

    assert data.iloc[0]['up_count'] == 1234
    assert data.iloc[0]['down_count'] == 456
    assert data.iloc[0]['neutral_count'] == 78
    assert data.iloc[0]['total_count'] == 2000
    assert data.iloc[0]['limit_up_count'] == 123
    assert data.iloc[0]['limit_down_count'] == 45
    assert data.iloc[0]['total_market_cap'] == 88.8 * 1e10


def test_adapter_parses_auction_details():
    adapter = EnhancedQuotesAdapter()

    def fake_json(path, params, hosts=None):
        assert path == '/api/qt/stock/details/get'
        assert params['secid'] == '0.000001'
        return {
            'data': {
                'details': [
                    '09:15:00,10.30,14,0,4',
                    '09:25:00,10.31,20,1000,2',
                    '09:30:00,10.32,30,2000,1',
                ]
            }
        }

    adapter._get_json = fake_json
    data = adapter.auction('000001')

    assert list(data['time']) == ['09:15:00', '09:25:00']
    assert list(data['price']) == [10.30, 10.31]
    assert list(data['code']) == ['000001', '000001']


def test_adapter_parses_fund_flow_and_filters_dates():
    adapter = EnhancedQuotesAdapter()

    def fake_json(path, params, hosts=None):
        assert path == '/api/qt/stock/fflow/daykline/get'
        return {
            'data': {
                'klines': [
                    '2026-07-01,1,2,3,4,5,0.1,0.2,0.3,0.4,0.5,10,1.1',
                    '2026-07-03,11,12,13,14,15,1.1,1.2,1.3,1.4,1.5,12,2.1',
                ]
            }
        }

    adapter._get_json = fake_json
    data = adapter.fund_flow('000001', start='20260702')

    assert list(data['date']) == ['2026-07-03']
    assert data.iloc[0]['main_net_amount'] == 11
    assert data.iloc[0]['super_net_pct'] == 1.5


def test_adapter_capital_flow_returns_latest_fund_flow_row():
    adapter = EnhancedQuotesAdapter()
    adapter.fund_flow = lambda symbol, **kwargs: pd.DataFrame(
        [
            {'code': symbol, 'date': '2026-07-01', 'main_net_amount': 1},
            {'code': symbol, 'date': '2026-07-03', 'main_net_amount': 3},
        ]
    )

    data = adapter.capital_flow('000001')

    assert len(data) == 1
    assert data.iloc[0]['date'] == '2026-07-03'
    assert data.iloc[0]['main_net_amount'] == 3


def test_adapter_parses_board_list_and_members():
    adapter = EnhancedQuotesAdapter()

    def fake_clist(fs, fields, count=10000):
        if fs == 'm:90+t:2':
            return [{'f12': 'BK0001', 'f13': 90, 'f14': '行业A', 'f2': 10, 'f3': 1.5, 'f4': 0.1, 'f5': 100, 'f6': 200}]
        if fs == 'b:BK0001':
            return [
                {'f12': '000001', 'f13': 0, 'f14': '平安银行', 'f2': 10, 'f3': 2.0, 'f4': 0.2, 'f5': 100, 'f6': 200},
                {'f12': '600036', 'f13': 1, 'f14': '招商银行', 'f2': 20, 'f3': -1.0, 'f4': -0.2, 'f5': 300, 'f6': 400},
            ]
        return []

    adapter._clist = fake_clist

    boards = adapter.boards('HY')
    members = adapter.board_members('BK0001')
    summary = adapter.board_summary('BK0001', members=True)
    ranking = adapter.board_ranking('HY', sort_by='amount', top=1)

    assert boards.iloc[0]['code'] == 'BK0001'
    assert members['code'].tolist() == ['000001', '600036']
    assert summary.iloc[0]['member_count'] == 2
    assert summary.iloc[0]['amount'] == 600
    assert summary.iloc[0]['up_count'] == 1
    assert summary.attrs['members'].equals(members)
    assert ranking.iloc[0]['name'] == '行业A'


def test_adapter_parses_symbol_info_and_provider_price_limits():
    adapter = EnhancedQuotesAdapter()

    def fake_stock_get(symbol, fields):
        return {
            'f57': '000001',
            'f58': '平安银行',
            'f43': 10.29,
            'f44': 10.4,
            'f45': 10.18,
            'f46': 10.29,
            'f47': 863327,
            'f48': 888789393.37,
            'f51': 11.31,
            'f52': 9.25,
            'f60': 10.28,
            'f62': -69118820,
            'f184': -7.78,
        }

    adapter._stock_get = fake_stock_get

    info = adapter.symbol_info('000001')
    limits = adapter.price_limits('000001')

    assert info.iloc[0]['name'] == '平安银行'
    assert info.iloc[0]['price'] == 10.29
    assert limits.iloc[0]['limit_up'] == 11.31
    assert limits.iloc[0]['limit_down'] == 9.25
    assert limits.iloc[0]['source'] == 'provider'


def test_adapter_price_limits_rule_fallbacks():
    adapter = EnhancedQuotesAdapter()
    adapter.symbol_info = lambda symbol: pd.DataFrame([{'code': symbol, 'name': '测试股票', 'pre_close': 10}])

    normal = adapter.price_limits('000001')
    star = adapter.price_limits('688001')
    st = adapter.price_limits('000001')

    assert normal.iloc[0]['limit_up'] == 11.0
    assert normal.iloc[0]['limit_down'] == 9.0
    assert star.iloc[0]['limit_up'] == 12.0

    adapter.symbol_info = lambda symbol: pd.DataFrame([{'code': symbol, 'name': '*ST测试', 'pre_close': 10}])
    st = adapter.price_limits('000001')
    assert st.iloc[0]['limit_up'] == 10.5
    assert st.iloc[0]['limit_down'] == 9.5


def test_adapter_belong_boards_uses_tdx_block_fallback():
    class FakeBase:
        def get_and_parse_block_info(self, filename):
            if filename == 'block_zs.dat':
                return [{'blockname': '银行', 'block_type': 0, 'code_index': 0, 'code': '000001'}]
            return [{'blockname': '中特估', 'block_type': 0, 'code_index': 1, 'code': '000001'}]

    adapter = EnhancedQuotesAdapter(base_client=FakeBase())
    data = adapter.belong_boards('000001')

    assert data['board_name'].tolist() == ['银行', '中特估']
    assert data['type'].tolist() == ['HY', 'GN']


@pytest.mark.online
def test_p1b_online_acceptance():
    client = Quotes.factory(market='std', bestip=True, timeout=5)

    try:
        auction = client.auction('000001')
        capital = client.capital_flow('000001')
        boards = client.boards('HY')
        members = client.board_members(boards.iloc[0]['code']) if not boards.empty else pd.DataFrame()
        belong = client.belong_boards('000001')
        stat = client.market_stat()
        info = client.symbol_info('000001')
        limits = client.price_limits('000001')

        assert isinstance(auction, pd.DataFrame)
        assert isinstance(capital, pd.DataFrame)
        assert isinstance(belong, pd.DataFrame)
        assert not boards.empty
        assert not members.empty
        assert not stat.empty
        assert not info.empty
        assert {'limit_up', 'limit_down'}.issubset(limits.columns)
    finally:
        client.close()
