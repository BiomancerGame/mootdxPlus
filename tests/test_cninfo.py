from pathlib import Path

import pandas as pd
import pytest

from mootdx.cninfo import CninfoClient
from mootdx.cninfo import CninfoError


class FakeResponse:
    def __init__(self, json_data=None, content=b''):
        self._json_data = json_data
        self.content = content

    def raise_for_status(self):
        return None

    def json(self):
        return self._json_data


class FakeHttp:
    def __init__(self):
        self.posts = []
        self.gets = []

    def get(self, url):
        self.gets.append(url)
        if url.endswith('szse_stock.json'):
            return FakeResponse({'stockList': [{'code': '000001', 'orgId': 'gssz0000001'}]})
        return FakeResponse(content=b'%PDF-1.4')

    def post(self, url, data):
        self.posts.append((url, data))
        return FakeResponse(
            {
                'announcements': [
                    {
                        'announcementTitle': 'Annual report',
                        'announcementTypeName': None,
                        'adjunctType': 'PDF',
                        'announcementId': '121',
                        'announcementTime': 1704067200000,
                        'adjunctUrl': 'new/disclosure/detail.pdf',
                    }
                ]
            }
        )


def test_get_announcements_parses_fields_and_orgid_mapping():
    http = FakeHttp()
    client = CninfoClient(client=http)

    data = client.get_announcements('000001', count=5, page=2)

    assert list(data.columns) == [
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
    assert data.iloc[0]['title'] == 'Annual report'
    assert data.iloc[0]['type'] == 'PDF'
    assert data.iloc[0]['date'] == '2024-01-01'
    assert data.iloc[0]['org_id'] == 'gssz0000001'
    assert data.iloc[0]['pdf_url'].startswith('https://www.cninfo.com.cn/')
    assert http.posts[0][1]['pageSize'] == '5'
    assert http.posts[0][1]['pageNum'] == '2'


def test_get_announcements_empty_result_has_columns():
    class EmptyHttp(FakeHttp):
        def post(self, url, data):
            return FakeResponse({'announcements': []})

    data = CninfoClient(client=EmptyHttp()).get_announcements('600036')

    assert isinstance(data, pd.DataFrame)
    assert data.empty
    assert 'pdf_url' in data.columns


def test_download_pdf_writes_file(tmp_path):
    client = CninfoClient(client=FakeHttp())
    row = {
        'pdf_url': 'https://www.cninfo.com.cn/test.pdf',
        'announcement_time': 1704067200000,
        'announcement_id': '121',
    }

    path = client.download_pdf(row, dest_dir=tmp_path)

    assert Path(path).read_bytes() == b'%PDF-1.4'
    assert Path(path).name == '20240101_121.PDF'


def test_download_pdf_requires_url(tmp_path):
    client = CninfoClient(client=FakeHttp())

    with pytest.raises(CninfoError):
        client.download_pdf({'pdf_url': ''}, dest_dir=tmp_path)


@pytest.mark.online
def test_cninfo_online_acceptance():
    data = CninfoClient(timeout=10).get_announcements('000001', count=5)

    assert not data.empty
    assert {'title', 'date', 'pdf_url'}.issubset(data.columns)
