import copy
import datetime
import io
import json
import shutil
from unittest import mock, skipUnless

import openpyxl
import requests
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from pypdf import PdfReader

from core.models import Operator

from .feed import parse_stations
from .models import TideGaugeRecord
from .reports import CHECK, CHECKED, build_workbook

HAS_LIBREOFFICE = shutil.which('soffice') or shutil.which('libreoffice')


def feed_row(net, code, location, datalatcy=5.0, feedlatcy=5.0, rep2show_diff='10.0'):
    """A station as served by /queries/latencies_location (only the fields that are read)."""
    return {'STATION_ID': code, 'NET': net, 'LOCATION': location, 'datalatcy': datalatcy, 'feedlatcy': feedlatcy,
            'rep2show_diff': rep2show_diff, 'current_ts': '2026-09-11T05:36:29.000Z'}


FEED = [
    feed_row('T1', 'MRRE', 'Marore, Kepulauan Sangihe, Sulawesi Utara, Indonesia'),
    feed_row('T1', 'ABGS', 'Air Bangis, Pasaman Barat, Sumatera Barat, Indonesia', feedlatcy=30,
             rep2show_diff='900'),  # 15.5 minutes old: Gaps.
    feed_row('WL', 'AWSSTA3047', 'AWS Maritim Padangbai'),
    feed_row('ID', 'ID301', 'P.Sebesi - Lampung - Sumatra', datalatcy=None, feedlatcy=None, rep2show_diff=None),
    feed_row('TO', 'ABAS', 'Abashiri, Japan', feedlatcy=10, rep2show_diff='30000'),  # 500 minutes old: Blank.
    feed_row('XX', 'NOPE', 'Not a network of the checklist'),
]


def sheet_values(sheet):
    return {cell.coordinate: cell.value for row in sheet.iter_rows() for cell in row if cell.value is not None}


class FeedTests(SimpleTestCase):
    def test_status_and_location_of_the_stations(self):
        data_time, stations = parse_stations(FEED)

        self.assertEqual(data_time, datetime.datetime(2026, 9, 11, 5, 36, 29, tzinfo=datetime.timezone.utc))
        self.assertEqual([(station['net'], station['code'], station['status']) for station in stations],
                         [('T1', 'ABGS', 'gaps'), ('T1', 'MRRE', 'normal'), ('WL', 'AWSSTA3047', 'normal'),
                          ('ID', 'ID301', 'blank'), ('TO', 'ABAS', 'blank')])
        self.assertEqual([(station['location'], station['region']) for station in stations],
                         [('Air Bangis , Pasaman Barat', 'Sumatera Barat'),
                          ('Marore , Kepulauan Sangihe', 'Sulawesi Utara'), ('AWS Maritim Padangbai', '-'),
                          ('P.Sebesi - Lampung', 'Sumatra'), ('Abashiri', 'Japan')])
        self.assertEqual((stations[0]['latency'], stations[3]['latency']), (15.5, None))


class TideGaugeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.operator = Operator.objects.create(name='Petugas Tide Gauge', NIP='444')
        cls.stations = parse_stations(FEED)[1]

    def post(self, stations, web_accessible=True, **values):
        data = {'date': '2026-09-11', 'shift': 'Pagi', 'kelompok': 2, 'operator': self.operator.pk,
                'check_time': '10:25', 'stations': json.dumps(stations), 'data_time': '2026-09-11T05:36:29+00:00',
                **values}
        if web_accessible:
            data['web_accessible'] = 'on'
        return self.client.post(reverse('tide_gauge:record_create'), data)

    def record(self, stations=None, **values):
        return TideGaugeRecord.objects.create(
            date=datetime.date(2026, 9, 11), shift='Pagi', kelompok=2, operator=self.operator,
            check_time=datetime.time(10, 25), stations=self.stations if stations is None else stations, **values)

    @mock.patch('tide_gauge.feed.requests.get')
    def test_fetch(self, get):
        get.return_value = mock.Mock(json=mock.Mock(return_value=FEED))

        data = self.client.post(reverse('api:tide_gauge:fetch')).json()

        self.assertEqual(len(data['stations']), 5)
        self.assertEqual(data['summary']['total'], {'total': 5, 'normal': 2, 'gaps': 1, 'spike': 0, 'blank': 2})
        self.assertEqual(data['data_time'], '2026-09-11T05:36:29Z')

    @mock.patch('tide_gauge.feed.requests.get', side_effect=requests.ConnectionError('No route to host'))
    def test_fetch_without_vpn(self, get):
        response = self.client.post(reverse('api:tide_gauge:fetch'))

        self.assertEqual(response.status_code, 502)
        self.assertIn('VPN', response.json()['error'])
        self.assertIn('172.19.3.224', response.json()['error'])

    def test_create_keeps_the_status_set_by_the_officer(self):
        stations = copy.deepcopy(self.stations)
        stations[1]['status'] = 'spike'

        response = self.post(stations)

        self.assertRedirects(response, reverse('tide_gauge:record_list'))
        record = TideGaugeRecord.objects.get()
        self.assertEqual(record.tg_id, 'TG-2026-09-11-2P')
        self.assertEqual(record.stations[1]['status'], 'spike')
        self.assertEqual((record.count_total, record.count_gaps, record.count_spike, record.count_blank), (5, 1, 1, 2))
        self.assertEqual(record.data_time, datetime.datetime(2026, 9, 11, 5, 36, 29, tzinfo=datetime.timezone.utc))

    def test_unknown_status_is_refused(self):
        stations = copy.deepcopy(self.stations)
        stations[0]['status'] = 'rusak'

        response = self.post(stations)

        self.assertContains(response, 'status tidak dikenal')
        self.assertFalse(TideGaugeRecord.objects.exists())

    def test_stations_are_needed_while_the_web_is_accessible(self):
        self.assertContains(self.post([]), 'Ambil data Tide Gauge')

        self.post([], web_accessible=False)

        self.assertEqual(TideGaugeRecord.objects.get().web_accessible, False)

    def test_one_checklist_per_duty(self):
        self.post(self.stations)

        response = self.post(self.stations, kelompok=3)

        self.assertContains(response, 'TG-2026-09-11-2P sudah ada')

    def test_workbook(self):
        stations = copy.deepcopy(self.stations)
        stations[1]['status'] = 'spike'
        sheet = build_workbook(self.record(stations)).active
        values = sheet_values(sheet)

        self.assertEqual(values['A1'], TideGaugeRecord.title)
        self.assertEqual((values['C3'], values['K3'], values['K4']), ('II (Dua)', '11 SEPTEMBER 2026', '10:25 WIB'))
        # Tide Gauge BIG: heading at row 8, header rows 11-12, stations from row 13.
        self.assertEqual(values['A8'], 'Tide Gauge BIG (T1)')
        self.assertIn(f'{CHECKED} Ya', values['A9'])
        self.assertEqual((values['B13'], values['C13'], values['D13'], values['E13']),
                         ('ABGS', 'Air Bangis , Pasaman Barat', 'Sumatera Barat', CHECK))
        self.assertEqual((values['B14'], values['F14']), ('MRRE', CHECK))
        # Then AWS-WL (no province column), IDSL and Tide Gauge IOC (country column), each 6 rows after the last.
        self.assertEqual((values['A16'], values['B21'], values['C21']),
                         ('AWS-WL BMKG (WL)', 'AWSSTA3047', 'AWS Maritim Padangbai'))
        self.assertIn('C21:D21', sheet.merged_cells)
        self.assertEqual((values['A23'], values['B28'], values['G28']), ('IDSL BRIN (ID)', 'ID301', CHECK))
        self.assertEqual((values['A30'], values['D33'], values['B35'], values['G35']),
                         ('Tide Gauge IOC (TO)', 'NEGARA', 'ABAS', CHECK))
        # Summary: 4 networks, then TOTAL KESELURUHAN and PERSENTASE.
        self.assertEqual((values['B38'], values['B39']), ('Sistem Platform', 'Tide Gauge BIG (T1)'))
        self.assertEqual([values[f'{column}43'] for column in 'AEGHJK'], ['TOTAL KESELURUHAN', 5, 1, 1, 2, 1])
        self.assertEqual([values[f'{column}44'] for column in 'EGHJK'], ['100%', '20.0%', '20.0%', '40.0%', '20.0%'])
        self.assertEqual((values['K47'], values['B49'], values['B53']),
                         ('Jakarta, 11 September 2026', 'Operator on Duty', '( Petugas Tide Gauge )'))
        self.assertEqual((sheet.page_setup.fitToWidth, sheet.page_setup.fitToHeight), (1, 0))

    def test_long_networks_take_two_blocks_and_buoys_sit_next_to_idsl(self):
        stations = [{'net': 'T1', 'code': f'T{number:03}', 'location': 'x', 'region': 'y', 'latency': 1,
                     'status': 'normal'} for number in range(1, 51)]
        stations += [{'net': net, 'code': code, 'location': 'x', 'region': 'y', 'latency': None, 'status': 'blank'}
                     for net, code in (('ID', 'ID301'), ('BY', 'BKG'))]
        values = sheet_values(build_workbook(self.record(stations, web_accessible=False)).active)

        self.assertEqual((values['B37'], values['I13'], values['J13'], values['J37']), ('T025', 26, 'T026', 'T050'))
        self.assertIn(f'{CHECKED} Tidak', values['A9'])
        self.assertEqual((values['A39'], values['I39'], values['B44'], values['J44']),
                         ('IDSL BRIN (ID)', 'InaBuoy BRIN (BY)', 'ID301', 'BKG'))

    def test_a_duty_job(self):
        record = self.record()

        data = self.client.get(reverse('api:duty_summary'), {'date': '2026-09-11', 'shift': 'P'}).json()

        codes = {job['key']: [row['code'] for row in job['records']] for job in data['slots'][0]['jobs']}
        self.assertEqual(codes['tide-gauge'], ['TG-2026-09-11-2P'])
        response = self.client.get(reverse('api:tide_gauge:record_xlsx', args=[record.pk]))
        self.assertEqual(openpyxl.load_workbook(io.BytesIO(response.content)).active['A1'].value, record.title)
        rows = self.client.get(reverse('api:tide_gauge:record_list'), {'page': 1}).json()['data']
        self.assertEqual((rows[0]['gaps'], rows[0]['blank']), (1, 2))

    @skipUnless(HAS_LIBREOFFICE, 'LibreOffice is not installed')
    def test_pdf(self):
        record = self.record()

        response = self.client.get(reverse('api:tide_gauge:record_pdf', args=[record.pk]))

        pages = PdfReader(io.BytesIO(response.content)).pages
        self.assertIn('TSUNAMI GAUGES', pages[0].extract_text())
