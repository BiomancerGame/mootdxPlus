from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode

import httpx
import pandas as pd


STOCK_MAP_URL = 'http://www.cninfo.com.cn/new/data/szse_stock.json'
QUERY_URL = 'https://www.cninfo.com.cn/new/hisAnnouncement/query'
BASE_URL = 'https://www.cninfo.com.cn'
ANNOUNCEMENT_COLUMNS = [
    'title',
    'type',
    'date',
    'url',
    'code',
    'org_id',
    'announcement_id',
    'announcement_time',
    'pdf_url',
]

_ORGID_MAP = {}


class CninfoError(Exception):
    """Cninfo request or parsing error."""


class CninfoClient:
    """Cninfo announcement search client."""

    def __init__(self, timeout=15.0, client=None):
        self.timeout = timeout
        self.client = client or httpx.Client(timeout=timeout, headers=self._headers())

    @staticmethod
    def _headers():
        return {
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            ),
            'Referer': 'https://www.cninfo.com.cn/new/disclosure',
            'Origin': 'https://www.cninfo.com.cn',
        }

    @staticmethod
    def _code(code):
        text = str(code).lower()
        for prefix in ('sh', 'sz', 'bj'):
            if text.startswith(prefix):
                return text[len(prefix):]
        return text.zfill(6)

    def _get_json(self, url):
        response = self.client.get(url)
        response.raise_for_status()
        return response.json()

    def _post_form(self, url, payload):
        response = self.client.post(url, data=payload)
        response.raise_for_status()
        return response.json()

    def _fetch_stock_map(self):
        data = self._get_json(STOCK_MAP_URL)
        stock_list = data.get('stockList', []) if isinstance(data, dict) else []
        return {str(item.get('code')).zfill(6): item.get('orgId') for item in stock_list if item.get('code')}

    def resolve_orgid(self, code):
        code = self._code(code)
        if not _ORGID_MAP:
            try:
                _ORGID_MAP.update(self._fetch_stock_map())
            except Exception:
                pass

        org_id = _ORGID_MAP.get(code)
        if org_id:
            return org_id
        if code.startswith('6'):
            return f'gssh0{code}'
        if code.startswith(('4', '8')):
            return f'gsbj0{code}'
        return f'gssz0{code}'

    def get_announcements(self, code, count=30, page=1):
        code = self._code(code)
        org_id = self.resolve_orgid(code)
        payload = {
            'stock': f'{code},{org_id}',
            'tabName': 'fulltext',
            'pageSize': str(int(count)),
            'pageNum': str(int(page)),
            'column': '',
            'category': '',
            'plate': '',
            'seDate': '',
            'searchkey': '',
            'secid': '',
            'sortName': '',
            'sortType': '',
            'isHLtitle': 'true',
        }

        try:
            data = self._post_form(QUERY_URL, payload)
        except Exception as exc:
            raise CninfoError(f'cninfo announcement query failed: {exc}') from exc

        items = data.get('announcements', []) if isinstance(data, dict) else []
        rows = [self._announcement_row(code, org_id, item) for item in items if isinstance(item, dict)]
        if not rows:
            return pd.DataFrame(columns=ANNOUNCEMENT_COLUMNS)
        return pd.DataFrame(rows, columns=ANNOUNCEMENT_COLUMNS)

    def download_pdf(self, row, dest_dir='.', filename=None):
        pdf_url = _get_field(row, 'pdf_url')
        if not pdf_url:
            raise CninfoError('announcement has no pdf_url')

        announcement_time = _get_field(row, 'announcement_time') or 0
        announcement_id = _get_field(row, 'announcement_id') or 'announcement'
        if filename is None:
            try:
                prefix = datetime.fromtimestamp(int(announcement_time) / 1000).strftime('%Y%m%d')
            except (TypeError, ValueError, OSError, OverflowError):
                prefix = 'unknown'
            filename = f'{prefix}_{announcement_id}.PDF'

        dest = Path(dest_dir)
        dest.mkdir(parents=True, exist_ok=True)
        filepath = dest / filename

        try:
            response = self.client.get(pdf_url)
            response.raise_for_status()
        except Exception as exc:
            raise CninfoError(f'cninfo pdf download failed: {exc}') from exc

        filepath.write_bytes(response.content)
        return os.path.abspath(filepath)

    def _announcement_row(self, code, org_id, item):
        announcement_id = str(item.get('announcementId') or '')
        announcement_time = item.get('announcementTime') or 0
        adjunct_url = item.get('adjunctUrl') or ''
        return {
            'title': item.get('announcementTitle') or '',
            'type': item.get('announcementTypeName') or item.get('adjunctType') or '',
            'date': _timestamp_to_date(announcement_time),
            'url': _detail_url(code, announcement_id, org_id, announcement_time),
            'code': code,
            'org_id': org_id,
            'announcement_id': announcement_id,
            'announcement_time': announcement_time,
            'pdf_url': _pdf_url(adjunct_url),
        }


def _timestamp_to_date(value):
    try:
        return datetime.fromtimestamp(int(value) / 1000).strftime('%Y-%m-%d')
    except (TypeError, ValueError, OSError, OverflowError):
        return str(value)[:10] if value else ''


def _pdf_url(path):
    if not path:
        return ''
    if str(path).startswith('http'):
        return str(path)
    return f'{BASE_URL}/{str(path).lstrip("/")}'


def _detail_url(code, announcement_id, org_id, announcement_time):
    query = urlencode(
        {
            'stockCode': code,
            'announcementId': announcement_id,
            'orgId': org_id,
            'announcementTime': announcement_time,
        }
    )
    return f'{BASE_URL}/new/disclosure/detail?{query}'


def _get_field(row, name):
    if isinstance(row, dict):
        return row.get(name)
    if isinstance(row, pd.Series):
        return row.get(name)
    return getattr(row, name, None)
