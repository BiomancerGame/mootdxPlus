import pandas as pd
import pytest

from mootdx.indicators import BOLL
from mootdx.indicators import KDJ
from mootdx.indicators import MACD
from mootdx.indicators import RSI
from mootdx.indicators import compute_indicators
from mootdx.indicators import list_indicators


def sample_data():
    return pd.DataFrame(
        {
            'open': [10, 11, 12, 13, 14, 15],
            'high': [11, 12, 13, 14, 15, 16],
            'low': [9, 10, 11, 12, 13, 14],
            'close': [10, 11, 12, 13, 14, 15],
            'vol': [100, 110, 120, 130, 140, 150],
        }
    )


def test_indicator_functions_append_expected_columns():
    df = sample_data()

    assert {'MACD_DIF', 'MACD_DEA', 'MACD_HIST'}.issubset(MACD(df).columns)
    assert {'KDJ_K', 'KDJ_D', 'KDJ_J'}.issubset(KDJ(df).columns)
    assert {'RSI'}.issubset(RSI(df).columns)
    assert {'BOLL_UPPER', 'BOLL_MID', 'BOLL_LOWER'}.issubset(BOLL(df).columns)


def test_compute_indicators_merges_multiple_indicators():
    data = compute_indicators(sample_data(), ['MACD', 'RSI'], params={'RSI': {'N': 3}})

    assert len(data) == 6
    assert 'MACD_DIF' in data.columns
    assert 'RSI' in data.columns
    assert data['RSI'].notna().all()


def test_indicator_missing_columns_raise_value_error():
    with pytest.raises(ValueError, match='missing columns'):
        KDJ(pd.DataFrame({'close': [1, 2, 3]}))


def test_list_indicators_contains_first_batch():
    names = {item['name'] for item in list_indicators()}

    assert {'MACD', 'KDJ', 'RSI', 'BOLL'} == names
