from io import StringIO

import pandas as pd

from core import feeds


class DataNotAvailable(Exception):
    pass


def events_table(csv):
    """Events stored as CSV (DailyReport.events, or the form before saving) as a table, times kept as text."""
    if not csv.strip():
        return pd.DataFrame(columns=feeds.DAILY_EVENT_COLUMNS)
    return pd.read_csv(StringIO(csv), dtype={'Date': str, 'OT (UTC)': str})


def fetch_day_events(day):
    """Events of the UTC day from index3.txt; DataNotAvailable once the feed no longer covers that day."""
    table = feeds.daily_events(day)
    if table.empty and day < feeds.events_available_since().date():
        raise DataNotAvailable(f'Data {day:%Y-%m-%d} sudah tidak ada di index3.txt (hanya berisi ±5 hari terakhir).')
    return table


def json_records(table):
    """Rows of a table for JSON, with missing values as null instead of NaN."""
    return table.astype(object).where(table.notna(), None).to_dict(orient='records')
