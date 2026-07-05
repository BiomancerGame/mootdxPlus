from __future__ import annotations

import httpx
import pandas as pd

from mootdx.consts import MARKET_SH
from mootdx.consts import MARKET_SZ
from mootdx.logger import logger
from mootdx.utils import get_stock_market


EASTMONEY_UT = 'bd1d9ddb04089700cf9c27f6f7426281'


class EnhancedQuotesAdapter:
    """Internal adapter for quote capabilities missing from tdxpy."""

    hosts = (
        'https://push2.eastmoney.com',
        'https://82.push2.eastmoney.com',
        'http://push2.eastmoney.com',
        'http://82.push2.eastmoney.com',
    )

    def __init__(self, base_client=None, timeout=10):
        self.base_client = base_client
        self.timeout = timeout or 10

    @staticmethod
    def _code(symbol):
        code = str(symbol).lower()
        for prefix in ('sh', 'sz'):
            if code.startswith(prefix):
                return code[len(prefix):]
        return code

    @staticmethod
    def _secid(symbol):
        code = EnhancedQuotesAdapter._code(symbol)
        market = get_stock_market(code, string=False)
        return f'{1 if market == MARKET_SH else 0}.{code}'

    @staticmethod
    def _market(symbol):
        return get_stock_market(EnhancedQuotesAdapter._code(symbol), string=False)

    @staticmethod
    def _empty(columns=None):
        return pd.DataFrame(columns=columns or [])

    @staticmethod
    def _normalize_date(value):
        if value is None:
            return None
        text = str(value)
        if len(text) == 8 and text.isdigit():
            return f'{text[:4]}-{text[4:6]}-{text[6:]}'
        return str(pd.to_datetime(value).date())

    @staticmethod
    def _normalize_compact_date(value):
        if value is None:
            return None
        return pd.to_datetime(value).strftime('%Y%m%d')

    @staticmethod
    def _to_number(value):
        if value in (None, '-', ''):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return value

    @staticmethod
    def _normalize_numeric(df, skip=None):
        skip = set(skip or [])
        for column in df.columns:
            if column in skip:
                continue
            converted = pd.to_numeric(df[column], errors='coerce')
            if not converted.isna().all():
                df[column] = converted
        return df

    def _get_json(self, path, params, hosts=None):
        headers = {
            'User-Agent': 'Mozilla/5.0',
            'Accept': 'application/json,text/plain,*/*',
            'Referer': 'https://quote.eastmoney.com/',
        }

        for host in hosts or self.hosts:
            url = f'{host}{path}'
            try:
                response = httpx.get(url, params=params, headers=headers, timeout=self.timeout)
                response.raise_for_status()
                return response.json()
            except Exception as exc:  # pragma: no cover - depends on live network
                logger.debug('enhanced quote request failed: %s %s', url, exc)

        return {}

    def _clist(self, fs, fields, count=10000):
        params = {
            'pn': 1,
            'pz': int(count),
            'po': 1,
            'np': 1,
            'ut': EASTMONEY_UT,
            'fltt': 2,
            'invt': 2,
            'fid': 'f3',
            'fs': fs,
            'fields': fields,
        }
        payload = self._get_json('/api/qt/clist/get', params)
        data = payload.get('data') or {}
        diff = data.get('diff') or []
        if isinstance(diff, dict):
            diff = list(diff.values())
        return diff

    def _stock_get(self, symbol, fields):
        params = {
            'secid': self._secid(symbol),
            'ut': EASTMONEY_UT,
            'fltt': 2,
            'invt': 2,
            'fields': fields,
        }
        payload = self._get_json('/api/qt/stock/get', params)
        return payload.get('data') or {}

    def auction(self, symbol, **kwargs):
        code = self._code(symbol)
        params = {
            'secid': self._secid(code),
            'pos': '-0',
            'fields1': 'f1,f2,f3,f4,f5',
            'fields2': 'f51,f52,f53,f54,f55',
        }
        payload = self._get_json('/api/qt/stock/details/get', params)
        details = (payload.get('data') or {}).get('details') or []
        rows = []

        for item in details:
            parts = str(item).split(',')
            if len(parts) < 5 or parts[0] >= '09:30:00':
                continue
            rows.append(
                {
                    'market': self._market(code),
                    'code': code,
                    'time': parts[0],
                    'price': self._to_number(parts[1]),
                    'volume': self._to_number(parts[2]),
                    'amount': self._to_number(parts[3]),
                    'bs_flag': self._to_number(parts[4]),
                }
            )

        data = pd.DataFrame(rows)
        if data.empty:
            return self._empty(['market', 'code', 'time', 'price', 'volume', 'amount', 'bs_flag'])
        return self._normalize_numeric(data, skip={'code', 'time'})

    def fund_flow(self, symbol, start=None, end=None, **kwargs):
        code = self._code(symbol)
        limit = int(kwargs.get('limit') or kwargs.get('count') or 120)
        params = {
            'secid': self._secid(code),
            'lmt': limit,
            'klt': 101,
            'fields1': 'f1,f2,f3,f7',
            'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63',
        }
        payload = self._get_json('/api/qt/stock/fflow/daykline/get', params)
        klines = (payload.get('data') or {}).get('klines') or []
        columns = [
            'date',
            'main_net_amount',
            'small_net_amount',
            'medium_net_amount',
            'large_net_amount',
            'super_net_amount',
            'main_net_pct',
            'small_net_pct',
            'medium_net_pct',
            'large_net_pct',
            'super_net_pct',
            'close',
            'change_pct',
        ]
        rows = []
        start_date = self._normalize_date(start)
        end_date = self._normalize_date(end)

        for item in klines:
            parts = str(item).split(',')
            if len(parts) < len(columns):
                continue
            row = dict(zip(columns, parts[: len(columns)]))
            row['date'] = self._normalize_date(row['date'])
            if start_date and row['date'] < start_date:
                continue
            if end_date and row['date'] > end_date:
                continue
            row['market'] = self._market(code)
            row['code'] = code
            rows.append(row)

        data = pd.DataFrame(rows)
        if data.empty:
            return self._empty(['market', 'code'] + columns)
        data = self._normalize_numeric(data, skip={'code', 'date'})
        return data.sort_values('date').reset_index(drop=True)

    def capital_flow(self, symbol, **kwargs):
        flow = self.fund_flow(symbol, **kwargs)
        if not flow.empty:
            return flow.tail(1).reset_index(drop=True)

        info = self.symbol_info(symbol)
        if info.empty:
            return self._empty()

        columns = ['market', 'code', 'name', 'main_net_amount', 'main_net_pct']
        return info[[column for column in columns if column in info.columns]]

    def minutes_recent(self, symbol, days=5, **kwargs):
        """Get recent multi-day minute trends from the enhanced provider."""

        return self._trends(symbol, days=days)

    def minute_extra(self, symbol, date=None, **kwargs):
        """Get minute auxiliary chart data when a provider exposes it."""

        data = self._trends(symbol, days=kwargs.get('days', 1))
        if data.empty:
            return self._empty(['market', 'code', 'datetime', 'date', 'time', 'avg_price', 'volume', 'amount'])
        if date is not None:
            target = self._normalize_date(date)
            data = data[data['date'] == target]
        columns = ['market', 'code', 'datetime', 'date', 'time', 'close', 'avg_price', 'volume', 'amount']
        return data[[column for column in columns if column in data.columns]]

    def mini_chart(self, symbol, date=None, **kwargs):
        """Get sampled mini chart data when a provider exposes it."""

        data = self.minute_extra(symbol, date=date, **kwargs)
        if data.empty:
            return self._empty(['market', 'code', 'datetime', 'date', 'time', 'close', 'avg_price'])

        points = kwargs.get('points')
        if points:
            points = max(1, int(points))
            step = max(1, (len(data) + points - 1) // points)
        else:
            step = max(1, int(kwargs.get('step', 5)))
        return data.iloc[::step].reset_index(drop=True)

    def _trends(self, symbol, days=1):
        code = self._code(symbol)
        params = {
            'secid': self._secid(code),
            'fields1': 'f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13',
            'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58',
            'ut': EASTMONEY_UT,
            'ndays': max(1, int(days)),
            'iscr': 0,
            'iscca': 0,
        }
        payload = self._get_json('/api/qt/stock/trends2/get', params)
        trends = (payload.get('data') or {}).get('trends') or []
        rows = []

        for item in trends:
            parts = str(item).split(',')
            if len(parts) < 8:
                continue
            timestamp = pd.to_datetime(parts[0], errors='coerce')
            if pd.isna(timestamp):
                continue
            rows.append(
                {
                    'market': self._market(code),
                    'code': code,
                    'datetime': timestamp,
                    'date': timestamp.strftime('%Y-%m-%d'),
                    'time': timestamp.strftime('%H:%M:%S'),
                    'open': self._to_number(parts[1]),
                    'close': self._to_number(parts[2]),
                    'high': self._to_number(parts[3]),
                    'low': self._to_number(parts[4]),
                    'volume': self._to_number(parts[5]),
                    'amount': self._to_number(parts[6]),
                    'avg_price': self._to_number(parts[7]),
                }
            )

        data = pd.DataFrame(rows)
        if data.empty:
            return self._empty(
                [
                    'market',
                    'code',
                    'datetime',
                    'date',
                    'time',
                    'open',
                    'close',
                    'high',
                    'low',
                    'volume',
                    'amount',
                    'avg_price',
                ]
            )
        data = self._normalize_numeric(data, skip={'code', 'datetime', 'date', 'time'})
        return data.set_index('datetime', drop=False).sort_index()

    def gbbq(self, symbol=None, filepath=None, **kwargs):
        """Read local GBBQ share-capital change records."""

        if not filepath:
            return self._empty(
                [
                    'market',
                    'code',
                    'datetime',
                    'date',
                    'category',
                    'liutong_before',
                    'total_before',
                    'liutong_after',
                    'total_after',
                ]
            )

        from mootdx.gbbq import read_gbbq

        try:
            data = read_gbbq(filepath)
        except Exception as exc:
            logger.debug('gbbq read failed: %s', exc)
            return self._empty()

        if symbol:
            code = self._code(symbol)
            data = data[data['code'].astype(str) == code]

        return data.reset_index(drop=True)

    def shares_at(self, symbol, date, **kwargs):
        """Estimate share capital at a date from GBBQ records."""

        code = self._code(symbol)
        target = self._normalize_compact_date(date)
        data = self.gbbq(symbol=code, **kwargs)
        row = {'market': self._market(code), 'code': code, 'date': self._normalize_date(date)}

        if data.empty:
            row.update({'total_shares': None, 'float_shares': None, 'source': 'empty'})
            return pd.DataFrame([row])

        frame = data.copy()
        frame['datetime'] = frame['datetime'].astype(str)
        frame = frame[frame['datetime'] <= target].sort_values('datetime')
        if frame.empty:
            row.update({'total_shares': None, 'float_shares': None, 'source': 'before_first_record'})
            return pd.DataFrame([row])

        latest = frame.iloc[-1]
        row.update(
            {
                'record_date': self._normalize_date(latest.get('datetime')),
                'total_shares': latest.get('total_after'),
                'float_shares': latest.get('liutong_after'),
                'source': 'gbbq',
            }
        )
        return pd.DataFrame([row])

    def turnover(self, symbol, date=None, volume=None, **kwargs):
        """Calculate turnover from volume and float shares."""

        code = self._code(symbol)
        target = date or pd.Timestamp.now().strftime('%Y%m%d')
        shares = self.shares_at(code, target, **kwargs)
        float_shares = shares.iloc[0].get('float_shares') if not shares.empty else None

        if volume is None:
            volume = self._latest_volume(code, date=target, **kwargs)

        try:
            value = float(volume)
            base = float(float_shares)
            turnover_rate = value / base * 100 if base > 0 else None
        except (TypeError, ValueError):
            turnover_rate = None

        return pd.DataFrame(
            [
                {
                    'market': self._market(code),
                    'code': code,
                    'date': self._normalize_date(target),
                    'volume': volume,
                    'float_shares': float_shares,
                    'turnover_rate': turnover_rate,
                }
            ]
        )

    def _latest_volume(self, code, date=None, **kwargs):
        quote = self._tdx_quote(code)
        return quote.get('vol') or quote.get('volume')

    def boards(self, type='HY', **kwargs):  # noqa: A002
        board_type = str(type or 'HY').upper()
        count = int(kwargs.get('count') or kwargs.get('limit') or 10000)

        if board_type == 'ALL':
            parts = [self.boards('HY', **kwargs), self.boards('GN', **kwargs)]
            parts = [part for part in parts if not part.empty]
            return pd.concat(parts, ignore_index=True) if parts else self._empty()

        fs_map = {
            'HY': 'm:90+t:2',
            'GN': 'm:90+t:3',
        }
        fields = 'f12,f13,f14,f2,f3,f4,f5,f6,f20,f21,f62'
        diff = self._clist(fs_map.get(board_type, str(type)), fields, count=count)
        rows = []

        for item in diff:
            rows.append(
                {
                    'type': board_type,
                    'market': item.get('f13'),
                    'code': item.get('f12'),
                    'name': item.get('f14'),
                    'price': item.get('f2'),
                    'change_pct': item.get('f3'),
                    'change': item.get('f4'),
                    'volume': item.get('f5'),
                    'amount': item.get('f6'),
                    'total_market_cap': item.get('f20'),
                    'float_market_cap': item.get('f21'),
                    'main_net_amount': item.get('f62'),
                }
            )

        data = pd.DataFrame(rows)
        if data.empty:
            return self._boards_from_tdx_block(board_type)
        return self._normalize_numeric(data, skip={'type', 'code', 'name'})

    def _boards_from_tdx_block(self, board_type):
        filename = {'HY': 'block_zs.dat', 'GN': 'block_gn.dat'}.get(board_type)
        if not filename or self.base_client is None:
            return self._empty(['type', 'code', 'name', 'member_count'])

        try:
            items = self.base_client.get_and_parse_block_info(filename) or []
        except Exception as exc:
            logger.debug('tdx block fallback failed: %s', exc)
            return self._empty(['type', 'code', 'name', 'member_count'])

        data = pd.DataFrame(items)
        if data.empty or 'blockname' not in data.columns:
            return self._empty(['type', 'code', 'name', 'member_count'])

        result = data.groupby('blockname', as_index=False).size()
        result = result.rename(columns={'blockname': 'name', 'size': 'member_count'})
        result['type'] = board_type
        result['code'] = result['name']
        return result[['type', 'code', 'name', 'member_count']]

    def board_members(self, code, **kwargs):
        board_code = str(code)
        count = int(kwargs.get('count') or kwargs.get('limit') or 10000)
        fields = 'f12,f13,f14,f2,f3,f4,f5,f6,f15,f16,f17,f18,f20,f21,f62'
        diff = self._clist(f'b:{board_code}', fields, count=count)
        rows = []

        for item in diff:
            rows.append(
                {
                    'board_code': board_code,
                    'market': item.get('f13'),
                    'code': item.get('f12'),
                    'name': item.get('f14'),
                    'price': item.get('f2'),
                    'change_pct': item.get('f3'),
                    'change': item.get('f4'),
                    'volume': item.get('f5'),
                    'amount': item.get('f6'),
                    'high': item.get('f15'),
                    'low': item.get('f16'),
                    'open': item.get('f17'),
                    'pre_close': item.get('f18'),
                    'total_market_cap': item.get('f20'),
                    'float_market_cap': item.get('f21'),
                    'main_net_amount': item.get('f62'),
                }
            )

        data = pd.DataFrame(rows)
        if data.empty:
            return self._board_members_from_tdx_block(board_code)
        return self._normalize_numeric(data, skip={'board_code', 'code', 'name'})

    def _board_members_from_tdx_block(self, code):
        if self.base_client is None:
            return self._empty(['board_code', 'code'])

        rows = []
        for board_type, filename in {'HY': 'block_zs.dat', 'GN': 'block_gn.dat'}.items():
            try:
                items = self.base_client.get_and_parse_block_info(filename) or []
            except Exception as exc:
                logger.debug('tdx board member fallback failed: %s', exc)
                continue
            for item in items:
                block_name = item.get('blockname')
                if block_name != code:
                    continue
                rows.append(
                    {
                        'type': board_type,
                        'board_code': code,
                        'board_name': block_name,
                        'code': item.get('code'),
                        'code_index': item.get('code_index'),
                    }
                )

        return pd.DataFrame(rows)

    def belong_boards(self, symbol, **kwargs):
        code = self._code(symbol)
        rows = []

        if self.base_client is None:
            return self._empty(['market', 'code', 'type', 'board_code', 'board_name'])

        for board_type, filename in {'HY': 'block_zs.dat', 'GN': 'block_gn.dat'}.items():
            try:
                items = self.base_client.get_and_parse_block_info(filename) or []
            except Exception as exc:
                logger.debug('tdx belong board fallback failed: %s', exc)
                continue

            for item in items:
                if str(item.get('code')) != code:
                    continue
                rows.append(
                    {
                        'market': self._market(code),
                        'code': code,
                        'type': board_type,
                        'board_code': item.get('blockname'),
                        'board_name': item.get('blockname'),
                        'block_type': item.get('block_type'),
                        'code_index': item.get('code_index'),
                    }
                )

        return pd.DataFrame(rows, columns=['market', 'code', 'type', 'board_code', 'board_name', 'block_type', 'code_index'])

    def board_summary(self, code, members=False, **kwargs):
        member_data = self.board_members(code, **kwargs)
        numeric = member_data.copy()
        for column in ['amount', 'volume', 'main_net_amount', 'change_pct', 'change', 'price', 'pre_close']:
            if column in numeric.columns:
                numeric[column] = pd.to_numeric(numeric[column], errors='coerce')

        up_count = down_count = 0
        if not numeric.empty:
            if 'change_pct' in numeric.columns:
                up_count = int((numeric['change_pct'] > 0).sum())
                down_count = int((numeric['change_pct'] < 0).sum())
            elif {'price', 'pre_close'}.issubset(numeric.columns):
                diff = numeric['price'] - numeric['pre_close']
                up_count = int((diff > 0).sum())
                down_count = int((diff < 0).sum())

        row = {
            'code': str(code),
            'name': str(code),
            'member_count': int(len(member_data)),
            'amount': float(numeric['amount'].sum()) if 'amount' in numeric.columns else 0.0,
            'volume': float(numeric['volume'].sum()) if 'volume' in numeric.columns else 0.0,
            'main_net_amount': float(numeric['main_net_amount'].sum()) if 'main_net_amount' in numeric.columns else 0.0,
            'up_count': up_count,
            'down_count': down_count,
        }

        if members:
            row['members'] = member_data.to_dict('records')

        result = pd.DataFrame([row])
        if members:
            result.attrs['members'] = member_data
        return result

    def board_ranking(self, type='HY', sort_by='change', top=None, **kwargs):  # noqa: A002
        data = self.boards(type=type, **kwargs)
        if data.empty:
            return data

        sort_map = {
            'change': 'change_pct',
            'change_pct': 'change_pct',
            'amount': 'amount',
            'volume': 'volume',
            'vol': 'volume',
            'main_net_amount': 'main_net_amount',
        }
        column = sort_map.get(sort_by, sort_by)
        if column in data.columns:
            data = data.sort_values(column, ascending=False)
        if top is not None:
            data = data.head(int(top))
        return data.reset_index(drop=True)

    def symbol_info(self, symbol, **kwargs):
        code = self._code(symbol)
        fields = (
            'f43,f44,f45,f46,f47,f48,f51,f52,f57,f58,f60,f71,f84,f85,f86,'
            'f107,f116,f117,f162,f167,f168,f169,f170,f171,f177,f184,f292,f62'
        )
        item = self._stock_get(code, fields)
        if not item:
            item = self._symbol_info_from_tdx_quote(code)
            if not item:
                return self._empty()

        row = {
            'market': self._market(code),
            'code': item.get('f57') or code,
            'name': item.get('f58'),
            'price': item.get('f43'),
            'high': item.get('f44'),
            'low': item.get('f45'),
            'open': item.get('f46'),
            'volume': item.get('f47'),
            'amount': item.get('f48'),
            'limit_up': item.get('f51'),
            'limit_down': item.get('f52'),
            'pre_close': item.get('f60'),
            'total_market_cap': item.get('f116'),
            'float_market_cap': item.get('f117'),
            'pe_dynamic': item.get('f162'),
            'pb': item.get('f167'),
            'turnover': item.get('f168'),
            'change': item.get('f169'),
            'change_pct': item.get('f170'),
            'amplitude': item.get('f171'),
            'main_net_amount': item.get('f62'),
            'main_net_pct': item.get('f184'),
            'trade_status': item.get('f292'),
        }
        data = pd.DataFrame([row])
        return self._normalize_numeric(data, skip={'code', 'name'})

    def _symbol_info_from_tdx_quote(self, code):
        quote = self._tdx_quote(code)
        if not quote:
            return {}

        return {
            'f57': quote.get('code') or code,
            'f58': quote.get('name'),
            'f43': quote.get('price'),
            'f44': quote.get('high'),
            'f45': quote.get('low'),
            'f46': quote.get('open'),
            'f47': quote.get('vol') or quote.get('volume'),
            'f48': quote.get('amount'),
            'f51': quote.get('limit_up'),
            'f52': quote.get('limit_down'),
            'f60': quote.get('last_close') or quote.get('pre_close'),
            'f62': quote.get('main_net_amount'),
            'f184': quote.get('main_net_pct'),
        }

    def price_limits(self, symbol, date=None, **kwargs):
        code = self._code(symbol)
        info = self.symbol_info(code)
        row = {'market': self._market(code), 'code': code, 'date': self._normalize_date(date)}

        if not info.empty:
            first = info.iloc[0]
            row['name'] = first.get('name')
            row['pre_close'] = first.get('pre_close')
            row['limit_up'] = first.get('limit_up')
            row['limit_down'] = first.get('limit_down')
            if pd.notna(row.get('limit_up')) and pd.notna(row.get('limit_down')):
                row['source'] = 'provider'
                return pd.DataFrame([row])

        name = row.get('name') or ''
        pre_close = row.get('pre_close')
        if date is not None:
            historical_pre_close = self._pre_close_from_daily_bars(code, date, max_pages=kwargs.get('max_pages', 5))
            if historical_pre_close is not None:
                pre_close = historical_pre_close

        if pre_close in (None, '') or pd.isna(pre_close):
            tdx_quote = self._tdx_quote(code)
            name = name or tdx_quote.get('name', '')
            pre_close = tdx_quote.get('last_close') or tdx_quote.get('pre_close') or pre_close

        limit_up, limit_down = self._compute_price_limits(code, name, pre_close)
        row.update(
            {
                'name': name,
                'pre_close': pre_close,
                'limit_up': limit_up,
                'limit_down': limit_down,
                'source': 'rule',
            }
        )
        return pd.DataFrame([row])

    def _tdx_quote(self, code):
        if self.base_client is None:
            return {}
        try:
            result = self.base_client.get_security_quotes([[self._market(code), code]]) or []
        except Exception as exc:
            logger.debug('tdx quote fallback failed: %s', exc)
            return {}
        return result[0] if result else {}

    def _pre_close_from_daily_bars(self, code, target_date, max_pages=5):
        if self.base_client is None:
            return None

        target = self._normalize_date(target_date)
        rows = []
        market = self._market(code)
        page_size = 800

        try:
            for page in range(int(max_pages)):
                result = self.base_client.get_security_bars(9, int(market), str(code), page * page_size, page_size)
                if not result:
                    break
                rows += result
                if len(result) < page_size:
                    break
        except Exception as exc:
            logger.debug('tdx daily bar fallback failed: %s', exc)
            return None

        data = pd.DataFrame(rows)
        if data.empty or 'datetime' not in data.columns or 'close' not in data.columns:
            return None

        data['date'] = pd.to_datetime(data['datetime']).dt.strftime('%Y-%m-%d')
        data = data.sort_values('date').reset_index(drop=True)
        matches = data.index[data['date'] == target].tolist()
        if not matches or matches[0] == 0:
            return None
        return data.loc[matches[0] - 1, 'close']

    def _compute_price_limits(self, code, name, pre_close):
        try:
            pre_close = float(pre_close)
        except (TypeError, ValueError):
            return None, None

        if pre_close <= 0 or self._is_index_like(code, name or ''):
            return None, None

        upper_name = str(name or '').upper()
        limit_pct = 0.10
        if 'ST' in upper_name:
            limit_pct = 0.05
        elif code.startswith(('688', '300', '301')):
            limit_pct = 0.20
        elif code.startswith(('43', '83', '87', '92')):
            limit_pct = 0.30

        return round(pre_close * (1 + limit_pct) + 0.00001, 2), round(pre_close * (1 - limit_pct) + 0.00001, 2)

    def _is_index_like(self, code, name):
        market = self._market(code)
        if market == MARKET_SH and code.startswith(('000', '880', '881', '882', '883', '884', '885', '999')):
            return True
        if market == MARKET_SZ and code.startswith(('395', '399')):
            return True
        return '指数' in name or '板块' in name
