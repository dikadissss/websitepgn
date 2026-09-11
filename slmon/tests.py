import datetime
import json
import shutil
import tempfile
from unittest import mock

import requests
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from daily_report import maps as base_maps
from daily_report.tests import solid_tile

from . import feed, maps
from .models import SlmonSnapshot
from .services import fetch_snapshot

DATA_TIME = datetime.datetime(2026, 9, 11, 5, 40, 57, tzinfo=datetime.timezone.utc)


def feature(code, lon, lat, colors):
    properties = {'net': 'IA', 'sta': code, 'time': '2026-09-11 05:40:57', 'country': 'Indonesia'}
    properties.update({f'color{number}': color for number, color in enumerate(colors, 1)})
    return {'type': 'Feature', 'properties': properties,
            'geometry': {'type': 'Point', 'coordinates': [str(lon), str(lat), 1]}}


STATUS = {'type': 'FeatureCollection', 'features': [
    feature('AAI', 128.194285, -3.687117, ['yellow', 'yellow', 'green', 'green', 'black', 'black']),
    feature('BBB', 110.0, -7.0, ['grey', 'black', 'red']),
    feature('CCC', 120.0, -2.0, ['grey', 'black', 'grey']),
    feature('DDD', 100.0, 0.5, ['black'] * 6),
    feature('EEE', 'x', 0.5, ['green']),  # No position: left out.
]}


def stations(green, black):
    return ([['IA', f'G{index}', 120.0, -2.0, 'green', 'green'] for index in range(green)]
            + [['IA', f'B{index}', 121.0, -3.0, 'grey', 'black'] for index in range(black)])


class StatusTests(SimpleTestCase):
    def test_station_status_is_its_best_channel_with_grey_counted_as_black(self):
        self.assertEqual(feed.station_color({'color1': 'yellow', 'color2': 'green'}), 'green')
        self.assertEqual(feed.station_color({'color1': 'grey', 'color3': 'red'}), 'red')
        self.assertEqual(feed.station_color({'color1': 'grey', 'color2': 'black'}), 'black')
        self.assertEqual(feed.station_color({}), 'black')

    def test_parse_keeps_color1_for_the_map_and_the_status_for_the_counts(self):
        data_time, parsed = feed.parse_status(STATUS)

        self.assertEqual(data_time, DATA_TIME)
        self.assertEqual(parsed[0], ['IA', 'AAI', 128.194285, -3.687117, 'yellow', 'green'])
        self.assertEqual([(code, color1, status) for _, code, _, _, color1, status in parsed[1:]],
                         [('BBB', 'grey', 'red'), ('CCC', 'grey', 'black'), ('DDD', 'black', 'black')])

    def test_unknown_or_empty_data(self):
        for data in ([], {}, {'features': []}):
            with self.assertRaises(feed.SlmonError):
                feed.parse_status(data)

    def test_download_errors(self):
        with mock.patch('slmon.feed.requests.get', side_effect=requests.ConnectionError('refused')):
            with self.assertRaises(feed.SlmonError):
                feed.fetch_status()

    def test_caption(self):
        snapshot = SlmonSnapshot(data_time=DATA_TIME, stations=stations(475, 71))

        self.assertEqual(snapshot.caption, (
            'Monitoring kondisi sinyal SeisComP (2026-09-11 12:40:57 WIB)\n'
            'Dalam Negeri : \n'
            '   Jumlah Sensor           : 546\n'
            '       :: Not Blank        : 475 (87.0 %)\n'
            '       :: Blank            : 71 (13.0 %)'
        ))
        self.assertEqual(len({line.rindex(':') for line in snapshot.caption.splitlines()[2:]}), 1)  # Colons aligned.
        self.assertEqual(snapshot.label, '2026-09-11 12:40 WIB · Blank 71/546')


@mock.patch('daily_report.maps.fetch_tile', side_effect=solid_tile)
@mock.patch('slmon.services.fetch_status', return_value=STATUS)
class SlmonTests(TestCase):
    def setUp(self):
        media, tiles = tempfile.mkdtemp(), tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, media)
        self.addCleanup(shutil.rmtree, tiles)
        settings_override = override_settings(MEDIA_ROOT=media, TILE_CACHE_DIR=tiles)
        settings_override.enable()
        self.addCleanup(settings_override.disable)

    def test_fetch_stores_the_snapshot_and_draws_its_map(self, *mocks):
        response = self.client.post(reverse('slmon:fetch'))

        snapshot = SlmonSnapshot.objects.get()
        self.assertRedirects(response, reverse('slmon:detail', args=[snapshot.pk]))
        self.assertEqual((snapshot.data_time, snapshot.total, snapshot.blank, snapshot.not_blank), (DATA_TIME, 4, 2, 2))
        self.assertEqual(snapshot.status_counts, {'green': 1, 'yellow': 0, 'orange': 0, 'red': 1, 'black': 2})
        colors = {}
        for path in (snapshot.map_path, snapshot.monitor_map_path):
            self.assertEqual(path.stat().st_mode & 0o777, 0o644)
            with Image.open(path) as image:
                self.assertEqual(image.size, maps.MONITOR_SIZE)
                colors[path] = {color for _, color in image.convert('RGB').getcolors(1 << 24)}
        # Stations take the color of their best channel on both maps (BBB is red, not grey).
        self.assertTrue({maps.COLORS['green'], maps.COLORS['red'], base_maps.NTWC_COLOR} <= colors[snapshot.map_path])
        self.assertTrue({maps.COLORS['red'], maps.PIE_COLORS['green']} <= colors[snapshot.monitor_map_path])
        self.assertNotIn(base_maps.NTWC_COLOR, colors[snapshot.monitor_map_path])
        page = self.client.get(reverse('slmon:index'))
        self.assertContains(page, snapshot.map_name)
        self.assertContains(page, snapshot.monitor_map_name)
        self.assertContains(page, ':: Blank            : 2 (50.0 %)')
        self.assertContains(page, 'id="slmon-chart"')

    def test_chart_of_the_last_days(self, *mocks):
        now = timezone.now()
        SlmonSnapshot.objects.create(data_time=now - datetime.timedelta(days=40), stations=stations(3, 3))
        SlmonSnapshot.objects.create(data_time=now - datetime.timedelta(days=2), stations=stations(5, 1))
        SlmonSnapshot.objects.create(data_time=now - datetime.timedelta(days=1), stations=stations(4, 2))

        def chart(**params):
            response = self.client.get(reverse('slmon:index'), params)
            data = json.loads(response.context['chart_json'])['data']
            return response.context['chart_days'], {trace['name']: list(trace['y']) for trace in data}

        self.assertEqual(chart(), (30, {'Not Blank': [5, 4], 'Blank': [1, 2]}))
        self.assertEqual(chart(days=90), (90, {'Not Blank': [3, 5, 4], 'Blank': [3, 1, 2]}))
        self.assertEqual(chart(days='x')[0], 30)

    def test_the_same_data_time_is_stored_once(self, *mocks):
        first, _ = fetch_snapshot()
        second, _ = fetch_snapshot()

        self.assertEqual((first.pk, SlmonSnapshot.objects.count()), (second.pk, 1))

    def test_feed_errors_are_shown(self, fetch_status, _):
        fetch_status.side_effect = feed.SlmonError('Data SLMON tidak dapat diambil: timeout')

        response = self.client.post(reverse('slmon:fetch'), follow=True)

        self.assertContains(response, 'Data SLMON tidak dapat diambil: timeout')
        self.assertFalse(SlmonSnapshot.objects.exists())

    def test_fetch_api(self, *mocks):
        data = self.client.post(reverse('api:slmon:fetch')).json()

        snapshot = SlmonSnapshot.objects.get()
        self.assertEqual((data['id'], data['total'], data['blank'], data['missing_tiles']), (snapshot.pk, 4, 2, 0))
        self.assertIn(snapshot.map_name, data['map_url'])
        self.assertIn(snapshot.monitor_map_name, data['monitor_map_url'])
        self.assertEqual(data['caption'], snapshot.caption)

    def test_fetch_api_error(self, fetch_status, _):
        fetch_status.side_effect = feed.SlmonError('down')

        response = self.client.post(reverse('api:slmon:fetch'))

        self.assertEqual((response.status_code, response.json()), (502, {'error': 'down'}))

    def test_snapshots_api_lists_the_last_days(self, *mocks):
        recent = SlmonSnapshot.objects.create(data_time=timezone.now(), stations=stations(2, 1))
        SlmonSnapshot.objects.create(data_time=timezone.now() - datetime.timedelta(days=10), stations=stations(2, 1))

        data = self.client.get(reverse('api:slmon:snapshots')).json()

        self.assertEqual([snapshot['id'] for snapshot in data['snapshots']], [recent.pk])

    def test_deleting_a_snapshot_removes_its_map(self, *mocks):
        snapshot, _ = fetch_snapshot()

        snapshot.delete()

        self.assertFalse(snapshot.map_path.exists())
        self.assertFalse(snapshot.monitor_map_path.exists())
