from __future__ import annotations

import struct
from pathlib import Path

import pandas as pd


_DAILY_FORMAT = struct.Struct('<IIIIIfII')
_LC_MINUTE_FORMAT = struct.Struct('<HHfffffII')


def write_daily(filepath, df, append=True, price_coeff=0.01, volume_coeff=0.01):
    """Write or append TDX .day records from a DataFrame."""

    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = _prepare_ohlcv(df, daily=True)

    if append:
        last_key = _last_daily_key(path)
        if last_key is not None:
            data = data[data['_key'] > last_key]
        mode = 'ab'
    else:
        mode = 'wb'

    if data.empty:
        if not append:
            path.write_bytes(b'')
        return 0

    payload = b''.join(
        _encode_daily(row, price_coeff=price_coeff, volume_coeff=volume_coeff) for _, row in data.iterrows()
    )
    with path.open(mode) as file:
        file.write(payload)
    return len(data)


def append_daily(filepath, df, **kwargs):
    """Append .day records, skipping dates already present at the file tail."""

    return write_daily(filepath, df, append=True, **kwargs)


def write_minute(filepath, df, kind='lc1', append=True):
    """Write or append TDX .lc1/.lc5 minute records from a DataFrame."""

    normalized_kind = str(kind).lower().lstrip('.')
    if normalized_kind not in {'lc1', 'lc5'}:
        raise ValueError("kind must be 'lc1' or 'lc5'")

    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = _prepare_ohlcv(df, daily=False)

    if append:
        last_key = _last_minute_key(path)
        if last_key is not None:
            data = data[data['_key'] > last_key]
        mode = 'ab'
    else:
        mode = 'wb'

    if data.empty:
        if not append:
            path.write_bytes(b'')
        return 0

    payload = b''.join(_encode_lc_minute(row) for _, row in data.iterrows())
    with path.open(mode) as file:
        file.write(payload)
    return len(data)


def append_minute(filepath, df, kind='lc1'):
    """Append .lc1/.lc5 minute records, skipping existing tail datetimes."""

    return write_minute(filepath, df, kind=kind, append=True)


def _prepare_ohlcv(df, daily):
    if df is None:
        return pd.DataFrame()

    data = pd.DataFrame(df).copy()
    if data.empty:
        return data

    missing = [column for column in ['open', 'high', 'low', 'close', 'amount'] if column not in data.columns]
    if missing:
        raise ValueError(f'DataFrame missing columns: {missing}')

    if 'volume' not in data.columns and 'vol' not in data.columns:
        raise ValueError("DataFrame missing columns: ['volume']")
    if 'volume' not in data.columns:
        data['volume'] = data['vol']

    datetimes = _resolve_datetime(data)
    data['_datetime'] = pd.to_datetime(datetimes)
    if data['_datetime'].isna().any():
        raise ValueError('DataFrame contains invalid datetime values')

    if daily:
        data['_key'] = data['_datetime'].dt.strftime('%Y%m%d').astype(int)
    else:
        data['_key'] = data['_datetime'].dt.strftime('%Y%m%d%H%M').astype(int)

    data = data.sort_values('_key').drop_duplicates('_key', keep='last')
    return data.reset_index(drop=True)


def _resolve_datetime(data):
    if 'datetime' in data.columns:
        return data['datetime']
    if 'date' in data.columns:
        return data['date']
    if isinstance(data.index, pd.DatetimeIndex):
        return data.index
    return data.index


def _encode_daily(row, price_coeff, volume_coeff):
    dt = row['_datetime']
    return _DAILY_FORMAT.pack(
        int(dt.strftime('%Y%m%d')),
        int(round(float(row['open']) / price_coeff)),
        int(round(float(row['high']) / price_coeff)),
        int(round(float(row['low']) / price_coeff)),
        int(round(float(row['close']) / price_coeff)),
        float(row['amount']),
        int(round(float(row['volume']) / volume_coeff)),
        0,
    )


def _encode_lc_minute(row):
    dt = row['_datetime']
    return _LC_MINUTE_FORMAT.pack(
        _encode_tdx_date(dt.year, dt.month, dt.day),
        _encode_tdx_time(dt.hour, dt.minute),
        float(row['open']),
        float(row['high']),
        float(row['low']),
        float(row['close']),
        float(row['amount']),
        int(round(float(row['volume']))),
        0,
    )


def _last_daily_key(path):
    if not path.is_file() or path.stat().st_size < _DAILY_FORMAT.size:
        return None
    size = path.stat().st_size
    size -= size % _DAILY_FORMAT.size
    if size < _DAILY_FORMAT.size:
        return None
    with path.open('rb') as file:
        file.seek(size - _DAILY_FORMAT.size)
        record = file.read(_DAILY_FORMAT.size)
    return int(_DAILY_FORMAT.unpack(record)[0])


def _last_minute_key(path):
    if not path.is_file() or path.stat().st_size < _LC_MINUTE_FORMAT.size:
        return None
    size = path.stat().st_size
    size -= size % _LC_MINUTE_FORMAT.size
    if size < _LC_MINUTE_FORMAT.size:
        return None
    with path.open('rb') as file:
        file.seek(size - _LC_MINUTE_FORMAT.size)
        record = file.read(_LC_MINUTE_FORMAT.size)
    date_num, time_num, *_ = _LC_MINUTE_FORMAT.unpack(record)
    year, month, day = _decode_tdx_date(date_num)
    hour, minute = _decode_tdx_time(time_num)
    return int(f'{year:04d}{month:02d}{day:02d}{hour:02d}{minute:02d}')


def _encode_tdx_date(year, month, day):
    return (int(year) - 2004) * 2048 + int(month) * 100 + int(day)


def _encode_tdx_time(hour, minute):
    return int(hour) * 60 + int(minute)


def _decode_tdx_date(value):
    year = int(value) // 2048 + 2004
    month = (int(value) % 2048) // 100
    day = (int(value) % 2048) % 100
    return year, month, day


def _decode_tdx_time(value):
    return int(value) // 60, int(value) % 60


__all__ = [
    'write_daily',
    'append_daily',
    'write_minute',
    'append_minute',
]
