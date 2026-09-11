"""Station status of the BMKG SeedLink monitor (slmon2), read from the JSON behind its page."""
import datetime

import requests

SLMON_URL = 'http://202.90.198.40/sismon-wrs/assets/sismon-slmon2/data/slmon.all.laststatus.json'
SLMON_PAGE_URL = 'http://202.90.198.40/sismon-wrs/web/slmon2'
REQUEST_TIMEOUT = 15
CHANNELS = 6
TIME_FORMAT = '%Y-%m-%d %H:%M:%S'

# Latency classes of a channel, best first, as ranked by the slmon2 table: a station takes the class of its best
# channel, and grey (no data for hours) counts as black. A black station is "Blank".
STATION_COLORS = ('green', 'yellow', 'orange', 'red', 'black')
COLOR_RANK = {'green': 0, 'yellow': 1, 'orange': 2, 'red': 3, 'grey': 4, 'black': 4}
BLANK = 'black'


class SlmonError(Exception):
    pass


def fetch_status():
    """The slmon JSON (a GeoJSON FeatureCollection with one feature per station)."""
    try:
        response = requests.get(SLMON_URL, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError) as error:
        raise SlmonError(f'Data SLMON tidak dapat diambil: {error}') from error


def station_color(properties):
    """Status of a station as in the slmon2 table: the class of its best channel, grey counted as black."""
    ranks = [COLOR_RANK[color] for color in (properties.get(f'color{n}') for n in range(1, CHANNELS + 1))
             if color in COLOR_RANK]
    return STATION_COLORS[min(ranks, default=COLOR_RANK[BLANK])]


def parse_status(data):
    """(time of the data as an aware UTC datetime, stations) of the slmon JSON.

    Each station is [network, code, longitude, latitude, color1, status]. The slmon2 page colors a station by its
    status (station_color) on the map, in the table and in the summary; color1 (the first channel) is kept too."""
    try:
        features = list(data['features'])
    except (KeyError, TypeError) as error:
        raise SlmonError('Format data SLMON tidak dikenal.') from error
    stations, times = [], set()
    for feature in features:
        properties = feature.get('properties') or {}
        try:
            lon, lat = (float(value) for value in feature['geometry']['coordinates'][:2])
        except (KeyError, TypeError, ValueError):
            continue
        color1 = properties.get('color1') if properties.get('color1') in COLOR_RANK else BLANK
        stations.append([properties.get('net', ''), properties.get('sta', ''), lon, lat, color1,
                         station_color(properties)])
        if properties.get('time'):
            times.add(properties['time'])
    if not stations:
        raise SlmonError('Data SLMON kosong.')
    try:
        data_time = datetime.datetime.strptime(max(times), TIME_FORMAT)
    except ValueError as error:
        raise SlmonError('Waktu data SLMON tidak dikenal.') from error
    return data_time.replace(tzinfo=datetime.timezone.utc), stations
