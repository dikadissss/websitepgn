"""Latency of the sea level stations (tsunami gauges, tide gauges, buoys, AWS and CBT), read from the JSON behind the
latency page of the InaTNT monitor (http://172.19.3.224:8080/). The server is on the BMKG network: it can only be
reached through the VPN.

A station's status follows the monitor and the old tools/Cheklist_TG_2026.py: no data or data older than 6 hours is
Blank, older than 10 minutes is Gaps. Spikes cannot be seen in the latency, so the officer marks them in the form."""
import datetime

import requests

TG_HOST = '172.19.3.224'
TG_API_URL = f'http://{TG_HOST}:3002/queries/latencies_location'
REQUEST_TIMEOUT = 15

# Networks in the order of the printed form, named as on the monitor's latency page.
CATEGORIES = (
    ('T1', 'Tide Gauge BIG'), ('T2', 'TG Realtime BIG'), ('TS', 'Tsunami Gauge BMKG'), ('WL', 'AWS-WL BMKG'),
    ('ID', 'IDSL BRIN'), ('BY', 'InaBuoy BRIN'), ('CT', 'InaCBT BRIN'), ('TO', 'Tide Gauge IOC'),
    ('DB', 'DartBuoy NOAA'), ('IC', 'TG INCOIS'),
)
CATEGORY_NAMES = dict(CATEGORIES)
NO_REGION = ('WL', 'DB', 'CT')  # Their location takes the province column too.
COUNTRY = ('TO', 'IC')          # The last part of their location is a country, not a province.
DASH_SEPARATED = ('ID', 'BY')   # 'P.Sebesi - Lampung - Sumatra'; the others use commas.

STATUSES = ('normal', 'gaps', 'spike', 'blank')
GAPS_MINUTES = 10
BLANK_MINUTES = 360


class TideGaugeError(Exception):
    pass


def heading(net):
    """'Tide Gauge BIG (T1)'."""
    return f'{CATEGORY_NAMES[net]} ({net})'


def has_region(net):
    return net not in NO_REGION


def region_header(net):
    return 'NEGARA' if net in COUNTRY else 'PROVINSI'


def categories():
    """The networks with their headings and table layout, for the form."""
    return [{'code': net, 'heading': heading(net), 'has_region': has_region(net), 'region_header': region_header(net)}
            for net, _ in CATEGORIES]


def fetch_latencies():
    """The latency JSON of the monitor: one object per station."""
    try:
        response = requests.get(TG_API_URL, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response.json()
    except (requests.ConnectionError, requests.Timeout) as error:
        raise TideGaugeError(f'Tidak dapat terhubung ke server Tide Gauge ({TG_HOST}). '
                             'Pastikan VPN BMKG tersambung, lalu coba lagi.') from error
    except (requests.RequestException, ValueError) as error:
        raise TideGaugeError(f'Data Tide Gauge tidak dapat diambil: {error}') from error


def data_age(station):
    """Age of the station's last data in seconds as the latency page shows it (its data_age()), None without data."""
    if station.get('datalatcy') is None or station.get('feedlatcy') is None:
        return None
    feed_latency = float(station['feedlatcy'])
    try:
        reported = float(station.get('rep2show_diff'))
    except (TypeError, ValueError):
        reported = 0.0
    return feed_latency if reported < 60 else reported + feed_latency


def station_status(age):
    if age is None or age > BLANK_MINUTES * 60:
        return 'blank'
    if age > GAPS_MINUTES * 60:
        return 'gaps'
    return 'normal'


def split_location(location, net):
    """(location, province or country) of the monitor's location text, as the printed form shows them."""
    location = str(location or '').strip()
    if location in ('', '-'):
        return '-', '-'
    if not has_region(net):
        return location, '-'
    separator = '-' if net in DASH_SEPARATED else ','
    parts = [part.strip() for part in location.split(separator)]
    if len(parts) == 1:
        return parts[0], '-'
    if parts[-1].upper() == 'INDONESIA':
        region, rest = parts[-2], parts[:-2]
    else:
        region, rest = parts[-1], parts[:-1]
    return f' {separator} '.join(rest).strip() or '-', region


def _parse_time(value):
    try:
        return datetime.datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    except ValueError:
        return None


def parse_stations(data):
    """(time of the data as an aware datetime or None, stations) of the latency JSON.

    A station is {net, code, location, region, latency (minutes, None without data), status}, ordered by network
    (CATEGORIES) then by code; stations of other networks are left out."""
    if not isinstance(data, list):
        raise TideGaugeError('Format data Tide Gauge tidak dikenal.')
    order = {net: index for index, (net, _) in enumerate(CATEGORIES)}
    stations, times = [], set()
    for row in data:
        if not isinstance(row, dict) or row.get('NET') not in order:
            continue
        net = row['NET']
        age = data_age(row)
        location, region = split_location(row.get('LOCATION'), net)
        stations.append({
            'net': net, 'code': str(row.get('STATION_ID') or '-').strip(), 'location': location, 'region': region,
            'latency': None if age is None else round(age / 60, 1), 'status': station_status(age),
        })
        if row.get('current_ts'):
            times.add(str(row['current_ts']))
    if not stations:
        raise TideGaugeError('Data Tide Gauge kosong.')
    stations.sort(key=lambda station: (order[station['net']], station['code']))
    return (_parse_time(max(times)) if times else None), stations


def group_stations(stations):
    """{network: its stations} in CATEGORIES order, without empty networks."""
    groups = {net: [] for net, _ in CATEGORIES}
    for station in stations:
        groups[station['net']].append(station)
    return {net: rows for net, rows in groups.items() if rows}


def count_statuses(stations):
    counts = dict.fromkeys(STATUSES, 0)
    for station in stations:
        counts[station['status']] += 1
    return {'total': len(stations), **counts}


def summary(stations):
    """Counts per network (in CATEGORIES order) and in total, with the percentages of the total."""
    networks = [{'net': net, 'heading': heading(net), **count_statuses(rows)}
                for net, rows in group_stations(stations).items()]
    total = count_statuses(stations)
    percent = {status: f"{total[status] / total['total'] * 100:.1f}%" if total['total'] else '0%'
               for status in STATUSES}
    return {'networks': networks, 'total': total, 'percent': percent}
