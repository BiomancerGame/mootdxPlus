from __future__ import annotations

from dataclasses import dataclass
from typing import Callable
from typing import Union

import numpy as np
import pandas as pd


def _series(values) -> pd.Series:
    return pd.Series(values, dtype='float64')


def _sma(values, window):
    return _series(values).rolling(window=int(window), min_periods=1).mean()


def _ema(values, span):
    return _series(values).ewm(span=int(span), adjust=False).mean()


def _std(values, window):
    return _series(values).rolling(window=int(window), min_periods=1).std(ddof=0)


def _round(values):
    return pd.Series(values).round(2)


@dataclass(frozen=True)
class IndicatorSpec:
    name: str
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    defaults: dict[str, Union[int, float]]
    description: str
    func: Callable[..., tuple[pd.Series, ...]]


def _macd(close, SHORT=12, LONG=26, M=9):  # noqa: N803
    dif = _ema(close, SHORT) - _ema(close, LONG)
    dea = dif.ewm(span=int(M), adjust=False).mean()
    hist = (dif - dea) * 2
    return _round(dif), _round(dea), _round(hist)


def _kdj(close, high, low, N=9, M1=3, M2=3):  # noqa: N803
    close = _series(close)
    high = _series(high)
    low = _series(low)
    low_n = low.rolling(window=int(N), min_periods=1).min()
    high_n = high.rolling(window=int(N), min_periods=1).max()
    spread = high_n - low_n
    rsv = ((close - low_n) / spread.replace(0, np.nan) * 100).fillna(50)
    k = rsv.ewm(com=int(M1) - 1, adjust=False).mean()
    d = k.ewm(com=int(M2) - 1, adjust=False).mean()
    j = k * 3 - d * 2
    return _round(k), _round(d), _round(j)


def _rsi(close, N=24):  # noqa: N803
    close = _series(close)
    diff = close.diff().fillna(0)
    up = diff.clip(lower=0)
    down = (-diff.clip(upper=0))
    avg_up = up.ewm(alpha=1 / int(N), adjust=False).mean()
    avg_down = down.ewm(alpha=1 / int(N), adjust=False).mean()
    rs = avg_up / avg_down.replace(0, np.nan)
    rsi = (100 - 100 / (1 + rs)).fillna(50)
    return (_round(rsi),)


def _boll(close, N=20, P=2):  # noqa: N803
    mid = _sma(close, N)
    std = _std(close, N)
    upper = mid + std * float(P)
    lower = mid - std * float(P)
    return _round(upper), _round(mid), _round(lower)


_REGISTRY = {
    'MACD': IndicatorSpec(
        'MACD',
        ('close',),
        ('MACD_DIF', 'MACD_DEA', 'MACD_HIST'),
        {'SHORT': 12, 'LONG': 26, 'M': 9},
        'MACD exponential moving average convergence divergence.',
        _macd,
    ),
    'KDJ': IndicatorSpec(
        'KDJ',
        ('close', 'high', 'low'),
        ('KDJ_K', 'KDJ_D', 'KDJ_J'),
        {'N': 9, 'M1': 3, 'M2': 3},
        'KDJ stochastic oscillator.',
        _kdj,
    ),
    'RSI': IndicatorSpec(
        'RSI',
        ('close',),
        ('RSI',),
        {'N': 24},
        'RSI relative strength index.',
        _rsi,
    ),
    'BOLL': IndicatorSpec(
        'BOLL',
        ('close',),
        ('BOLL_UPPER', 'BOLL_MID', 'BOLL_LOWER'),
        {'N': 20, 'P': 2},
        'Bollinger bands.',
        _boll,
    ),
}


def list_indicators():
    return [
        {
            'name': spec.name,
            'inputs': list(spec.inputs),
            'outputs': list(spec.outputs),
            'default_params': dict(spec.defaults),
            'description': spec.description,
        }
        for spec in _REGISTRY.values()
    ]


def _compute_one(df, name, params=None):
    key = str(name).upper()
    if key not in _REGISTRY:
        raise ValueError(f'unknown indicator: {name}')

    spec = _REGISTRY[key]
    missing = [column for column in spec.inputs if column not in df.columns]
    if missing:
        raise ValueError(f'DataFrame missing columns for {key}: {missing}')

    kwargs = dict(spec.defaults)
    kwargs.update(params or {})
    arrays = spec.func(*(df[column].to_numpy(dtype='float64') for column in spec.inputs), **kwargs)
    return pd.DataFrame({column: value.to_numpy() for column, value in zip(spec.outputs, arrays)}, index=df.index)


def compute_indicators(df, indicators, params=None):
    if isinstance(indicators, str):
        indicators = [indicators]

    result = df.copy()
    params = params or {}
    parts = []
    for name in indicators:
        key = str(name).upper()
        parts.append(_compute_one(result, key, params.get(key) or params.get(name) or {}))

    if parts:
        result = pd.concat([result, *parts], axis=1)
    return result


def MACD(df, SHORT=12, LONG=26, M=9):  # noqa: N802,N803
    return compute_indicators(df, ['MACD'], {'MACD': {'SHORT': SHORT, 'LONG': LONG, 'M': M}})


def KDJ(df, N=9, M1=3, M2=3):  # noqa: N802,N803
    return compute_indicators(df, ['KDJ'], {'KDJ': {'N': N, 'M1': M1, 'M2': M2}})


def RSI(df, N=24):  # noqa: N802,N803
    return compute_indicators(df, ['RSI'], {'RSI': {'N': N}})


def BOLL(df, N=20, P=2):  # noqa: N802,N803
    return compute_indicators(df, ['BOLL'], {'BOLL': {'N': N, 'P': P}})
