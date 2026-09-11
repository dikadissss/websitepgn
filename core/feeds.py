"""Earthquake bulletins published by the BMKG server, parsed into the tables the QC/BAST forms start from."""
import datetime

import pandas as pd
import requests
from django.core.cache import cache

EVENTS_URL = 'http://202.90.198.41/index3.txt'
FOCAL_MECHANISMS_URL = 'http://202.90.198.41/qc_focal.txt'
CACHE_SECONDS = 60
REQUEST_TIMEOUT = 15

QC_EVENT_COLUMNS = ['Date', 'OT (UTC)', 'Lat', 'Long', 'Mag', 'TypeMag', 'D(Km)', 'Phase', 'RMS', 'Az. Gap', 'Region']
BAST_EVENT_COLUMNS = ['Date', 'OT (UTC)', 'Lat', 'Long', 'D(Km)', 'Mag', 'TypeMag', 'Region']
BAST_EMPTY_COLUMNS = ['MMI', 'Dis. PGN', 'Selisih PGN', 'Dis. PGR', 'Selisih PGR']
DAILY_EVENT_COLUMNS = ['Date', 'OT (UTC)', 'Lat', 'Long', 'D(Km)', 'Mag', 'TypeMag', 'Region']
FOCAL_MECHANISM_COLUMNS = ['Date', 'OT (UTC)', 'Lat', 'Long', 'Mag', 'TypeMag', 'D(Km)',
                           'S1', 'D1', 'R1', 'S2', 'D2', 'R2', 'Fit(%)', 'CLVD(%)']


class FeedError(Exception):
    pass


def _download(url):
    """Fetch a bulletin, reusing the copy downloaded in the last minute."""
    text = cache.get(url)
    if text is None:
        try:
            response = requests.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
        except requests.RequestException as error:
            raise FeedError(f'Failed to fetch {url}: {error}') from error
        text = response.content.decode('utf-8')
        cache.set(url, text, CACHE_SECONDS)
    return text


def _parse_table(lines):
    rows = ['|'.join(part.strip() for part in line.split('|')).split('|') for line in lines]
    return pd.DataFrame(rows[1:], columns=rows[0])


def _select_period(df, time_column, start, end):
    """Keep rows within [start, end], sorted by time, with the time split into 'Date' and 'OT (UTC)'."""
    df[time_column] = pd.to_datetime(df[time_column], format='%Y-%m-%d %H:%M:%S')
    df = df[(df[time_column] >= start) & (df[time_column] <= end)].sort_values(by=time_column)
    df = df.assign(**{'Date': df[time_column].dt.date, 'OT (UTC)': df[time_column].dt.time})
    return df.drop(columns=time_column).reset_index(drop=True)


def events(start, end):
    """Events (index3.txt) between start and end, with the bulletin's column names normalized."""
    lines = [line for index, line in enumerate(_download(EVENTS_URL).split('\n')) if index not in (0, 1, 3)]
    df = _select_period(_parse_table(lines), 'Origin Time (GMT)', start, end)
    df = df.rename(columns={'Lon': 'Long', 'Depth': 'D(Km)', 'cntP': 'Phase', 'AZgap': 'Az. Gap', 'Remarks': 'Region'})
    return df.loc[:, ~df.columns.duplicated()]


def qc_events(start, end):
    return events(start, end)[QC_EVENT_COLUMNS]


def bast_events(start, end):
    df = events(start, end)[BAST_EVENT_COLUMNS].reset_index(drop=True)
    df.insert(0, 'No', range(1, len(df) + 1))
    return df.assign(**{column: '' for column in BAST_EMPTY_COLUMNS})


def focal_mechanisms(start, end):
    """Focal mechanisms (qc_focal.txt) between start and end."""
    df = _select_period(_parse_table(_download(FOCAL_MECHANISMS_URL).split('\n')), 'Datetime (UTC)', start, end)
    df = df.rename(columns={'D': 'D(Km)', 'Type M': 'TypeMag'})
    return df[FOCAL_MECHANISM_COLUMNS]


def numbered(df):
    """Copy of df with a leading 1-based 'No' column, as shown in the form tables."""
    return df.reset_index(drop=True).assign(No=range(1, len(df) + 1))[['No', *df.columns]]


def daily_events(day):
    """Every event (manual and automatic) of one UTC day, in time order, with coordinates written as in the PDE.

    Magnitudes stay as published (two decimals); the PDE cells display them with one decimal."""
    start = datetime.datetime.combine(day, datetime.time.min)
    end = datetime.datetime.combine(day, datetime.time(23, 59, 59))
    df = events(start, end)[DAILY_EVENT_COLUMNS].reset_index(drop=True)
    df['Mag'] = pd.to_numeric(df['Mag'], errors='coerce')
    for column in ('Lat', 'Long'):
        df[column] = df[column].map(trim_coordinate)
    return df


def trim_coordinate(text):
    """'178.68600 E' -> '178.686 E'"""
    value, _, hemisphere = str(text).strip().partition(' ')
    if '.' in value:
        value = value.rstrip('0').rstrip('.')
    return f'{value} {hemisphere.strip()}'.strip()


def events_available_since():
    """Origin time of the oldest event still listed in index3.txt (the feed only keeps about five days)."""
    lines = [line for index, line in enumerate(_download(EVENTS_URL).split('\n')) if index not in (0, 1, 3)]
    return pd.to_datetime(_parse_table(lines)['Origin Time (GMT)'], format='%Y-%m-%d %H:%M:%S', errors='coerce').min()


def parse_coordinate(text):
    """'8.12901 S' -> -8.12901, '120.43388 E' -> 120.43388."""
    value, _, hemisphere = str(text).strip().partition(' ')
    number = float(value)
    return -number if hemisphere.strip().upper() in ('S', 'W') else number


def parse_depth(text):
    """'10 km' -> 10.0"""
    return float(str(text).split()[0])
