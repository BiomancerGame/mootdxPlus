import pandas as pd

from mootdx.gbbq import read_gbbq
from mootdx.quotes import StdQuotes


def test_read_gbbq_csv_normalizes_alias_columns(tmp_path):
    filepath = tmp_path / 'gbbq.csv'
    pd.DataFrame(
        [
            {
                'market': 0,
                'code': '1',
                'date': '2020-01-01',
                'category': 5,
                'panqianliutong': 80,
                'qianzongguben': 100,
                'panhouliutong': 90,
                'houzongguben': 110,
            }
        ]
    ).to_csv(filepath, index=False)

    data = read_gbbq(filepath)

    assert data.iloc[0]['code'] == '000001'
    assert data.iloc[0]['datetime'] == 20200101
    assert data.iloc[0]['liutong_after'] == 90
    assert data.iloc[0]['total_after'] == 110


def test_adapter_shares_at_and_turnover_from_gbbq_csv(tmp_path):
    filepath = tmp_path / 'gbbq.csv'
    pd.DataFrame(
        [
            {
                'market': 0,
                'code': '000001',
                'datetime': 20200101,
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
                'category': 5,
                'liutong_before': 90,
                'total_before': 110,
                'liutong_after': 100,
                'total_after': 120,
            },
        ]
    ).to_csv(filepath, index=False)

    client = StdQuotes.__new__(StdQuotes)
    client.client = None

    shares = client.shares_at('000001', '2020-12-31', filepath=filepath)
    turnover = client.turnover('000001', '2020-12-31', volume=9, filepath=filepath)

    assert shares.iloc[0]['total_shares'] == 110
    assert shares.iloc[0]['float_shares'] == 90
    assert turnover.iloc[0]['turnover_rate'] == 10.0
