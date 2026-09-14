import datetime
import io
import shutil
import tempfile
from pathlib import Path
from unittest import mock, skipUnless

import openpyxl
from django.conf import settings
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from PIL import Image
from pypdf import PdfReader

from core import feeds
from core.choices import Shift
from core.models import Operator
from qc.models import QcRecord

from . import maps
from .models import DailyReport

REPORT_DATE = datetime.date(2026, 9, 7)
FEED = (
    " List of real time automatic BMKG earthquake locations::five days of SEISCOMP3 data:: \n"
    " ....................................................\n"
    " | Origin Time (GMT)   | Status    |cntP |Mag  |TypeMag |cntM |AZgap| RMS |Lat      | Lon      | Depth  | Remarks\n"
    " ....................................................\n"
    " | 2026-09-08 00:10:00 | manual    | 30  | 3.12 | M      | 20 | 58  | 1.7 | 1.5 S  | 120.5 E | 10 km  | Next Day Region\n"
    " | 2026-09-07 23:51:27 | automatic | 30  | 2.64 | M      | 20 | 58  | 1.7 | 8.36155 S  | 121.32470 E | 10 km  | Flores Region, Indonesia\n"
    " | 2026-09-07 05:50:40 | manual    | 30  | 5.52 | mb     | 20 | 58  | 1.7 | 23.39138 S  | 172.5208 E | 10 km  | Southeast of Loyalty Islands\n"
    " | 2026-09-07 00:30:43 | manual    | 30  | 3.1  | M      | 20 | 58  | 1.7 | 8.12901 S  | 120.43388 E | 610 km  | Flores Sea\n"
    " | 2026-09-06 23:59:59 | manual    | 30  | 4.0  | M      | 20 | 58  | 1.7 | 2.0 N  | 126.0 E | 33 km  | Previous Day Region\n"
)


def solid_tile(*args):
    buffer = io.BytesIO()
    Image.new('RGB', (maps.TILE_SIZE, maps.TILE_SIZE), (170, 200, 230)).save(buffer, 'PNG')
    return buffer.getvalue()


@mock.patch('core.feeds._download', return_value=FEED)
class DailyEventsTests(SimpleTestCase):
    def test_every_event_of_the_utc_day_whatever_its_status(self, _download):
        table = feeds.daily_events(REPORT_DATE)

        self.assertEqual(list(table['OT (UTC)'].astype(str)), ['00:30:43', '05:50:40', '23:51:27'])
        self.assertEqual(list(table['Mag']), [3.1, 5.52, 2.64])
        self.assertEqual(list(table['Long']), ['120.43388 E', '172.5208 E', '121.3247 E'])
        self.assertEqual(list(table['Region']), ['Flores Sea', 'Southeast of Loyalty Islands', 'Flores Region, Indonesia'])

    def test_feed_start(self, _download):
        self.assertEqual(feeds.events_available_since().date(), datetime.date(2026, 9, 6))


class MapGeometryTests(SimpleTestCase):
    def test_coordinates(self):
        self.assertEqual(feeds.parse_coordinate('8.12901 S'), -8.12901)
        self.assertEqual(feeds.parse_coordinate('120.43388 E'), 120.43388)
        self.assertEqual(feeds.parse_coordinate('2.5 N'), 2.5)
        self.assertEqual(feeds.parse_depth('610 km'), 610.0)

    def test_bounds_follow_the_events(self):
        west, south, east, north = maps.map_bounds([(120.0, -8.0, 10, 3.0), (130.0, -2.0, 10, 4.0)])

        self.assertTrue(west < 120 < 130 < east)
        self.assertTrue(south < -8 < -2 < north)
        self.assertGreaterEqual(east - west, maps.MIN_LON_SPAN)

    def test_bounds_stay_continuous_across_the_antimeridian(self):
        west, _, east, _ = maps.map_bounds([(178.0, -20.0, 10, 5.0), (-178.0, -15.0, 10, 5.0)])

        self.assertTrue(west < 178 and east > 182)
        self.assertLess(east - west, 40)

    def test_default_area_without_events(self):
        self.assertEqual(maps.map_bounds([]), maps.DEFAULT_BOUNDS)

    def test_legend_classes(self):
        self.assertEqual([maps.depth_color(depth) for depth in (60, 61, 300, 301)],
                         [(230, 0, 0), (255, 235, 0), (255, 235, 0), (0, 205, 0)])
        self.assertEqual([maps.marker_radius(magnitude) for magnitude in (4.0, 4.1, 5.0, 5.1)], [7, 10, 10, 14])


@mock.patch('daily_report.maps.fetch_tile', side_effect=solid_tile)
@mock.patch('core.feeds._download', return_value=FEED)
class DailyReportTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.officer = Operator.objects.create(name='Petugas Onduty', NIP='111')
        cls.spv = Operator.objects.create(name='Supervisor Dinas', NIP='222')

    def setUp(self):
        media, tiles = tempfile.mkdtemp(), tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, media)
        self.addCleanup(shutil.rmtree, tiles)
        settings_override = override_settings(MEDIA_ROOT=media, TILE_CACHE_DIR=tiles)
        settings_override.enable()
        self.addCleanup(settings_override.disable)

    def create_report(self):
        response = self.client.post(reverse('daily_report:dailyreport_create'), {
            'report_date': '2026-09-07', 'kelompok': 2, 'operator': self.officer.pk, 'events': '',
        })
        report = DailyReport.objects.get()
        self.assertRedirects(response, reverse('daily_report:dailyreport_update', args=[report.pk]))
        return report

    def test_report_belongs_to_the_pagi_duty_of_the_next_day(self, *mocks):
        report = DailyReport.objects.create(report_date=REPORT_DATE, kelompok=2, operator=self.officer, spv=self.spv)

        self.assertEqual((report.report_id, report.date, report.shift), ('DR-2026-09-07', datetime.date(2026, 9, 8), Shift.PAGI))

    def test_saving_stores_the_events_and_draws_the_map_file(self, *mocks):
        report = self.create_report()

        self.assertEqual(len(report.event_table()), 3)
        self.assertTrue(report.map_path.exists())
        self.assertEqual(report.map_path.stat().st_mode & 0o777, 0o644)  # Readable by nginx (www-data).
        with Image.open(report.map_path) as image:
            self.assertEqual(image.size, (maps.MAP_SIZE[0] + 2 * maps.FRAME, maps.MAP_SIZE[1] + 2 * maps.FRAME))
        page = self.client.get(reverse('daily_report:dailyreport_update', args=[report.pk]))
        self.assertContains(page, report.map_url)
        self.assertContains(page, 'Southeast of Loyalty Islands')
        self.assertNotContains(page, reverse('api:daily_report:record_xlsx', args=[report.pk]))  # Exports are on Rekap.

    def test_map_can_be_plotted_again_from_the_stored_events(self, *mocks):
        report = self.create_report()
        report.map_path.unlink()

        data = self.client.post(reverse('api:daily_report:record_map', args=[report.pk])).json()

        self.assertTrue(report.map_path.exists())
        self.assertEqual(data['missing_tiles'], 0)
        self.assertTrue(data['map_url'].startswith(report.map_url))

    def test_events_api(self, *mocks):
        data = self.client.get(reverse('api:daily_report:events'), {'date': '2026-09-07'}).json()

        self.assertEqual(data['count'], 3)
        self.assertEqual((data['rows'][0]['No'], data['rows'][0]['Region']), (1, 'Flores Sea'))

    def test_map_preview_of_events_not_saved_yet(self, *mocks):
        csv = self.client.get(reverse('api:daily_report:events'), {'date': '2026-09-07'}).json()['csv']

        response = self.client.post(reverse('api:daily_report:map_preview'), {'events': csv})

        self.assertEqual((response['Content-Type'], response['X-Missing-Tiles']), ('image/png', '0'))
        with Image.open(io.BytesIO(response.content)) as image:
            self.assertEqual(image.size, (maps.MAP_SIZE[0] + 2 * maps.FRAME, maps.MAP_SIZE[1] + 2 * maps.FRAME))
            self.assertIn(maps.NTWC_COLOR, {color for _, color in image.convert('RGB').getcolors(1 << 24)})
        self.assertEqual(list(Path(settings.MEDIA_ROOT).iterdir()), [])

    def test_map_preview_of_invalid_events(self, *mocks):
        response = self.client.post(reverse('api:daily_report:map_preview'), {'events': 'Lat,Long\nx,y\n'})

        self.assertEqual(response.status_code, 400)

    def test_events_api_for_a_day_the_feed_no_longer_lists(self, *mocks):
        response = self.client.get(reverse('api:daily_report:events'), {'date': '2026-09-01'})

        self.assertEqual(response.status_code, 404)
        self.assertIn('index3.txt', response.json()['error'])

    def test_report_workbook_is_the_map_page_then_the_pde(self, *mocks):
        report = self.create_report()

        response = self.client.get(reverse('api:daily_report:record_xlsx', args=[report.pk]))
        self.assertEqual(response['Content-Disposition'], 'attachment; filename=Daily_Report_2026-09-07.xlsx')
        workbook = openpyxl.load_workbook(io.BytesIO(response.content))
        self.assertEqual(workbook.sheetnames, ['Peta', '07-09-2026'])
        self.assertEqual(len(workbook['Peta']._images), 1)
        self.assertEqual(workbook['Peta'].page_setup.orientation, 'landscape')
        sheet = workbook['07-09-2026']
        self.assertEqual(sheet['A10'].value, 'Preliminary Determination of Epicenter, September 07, 2026')
        self.assertEqual([sheet[f'A{row}'].value for row in (13, 14, 15)], [1, 2, 3])
        self.assertEqual((sheet['C13'].value, sheet['F13'].value, sheet['G14'].value, sheet['H14'].value),
                         (datetime.time(0, 30, 43), '610 km', 5.52, 'mb'))
        self.assertEqual(sheet['G14'].number_format, '0.0')  # Shown as 5.5.
        self.assertEqual(sheet['G17'].value, 'Jakarta, 08 September 2026')
        self.assertEqual((sheet['B18'].value, sheet['G18'].value), ('Petugas onduty', 'Mengetahui'))
        self.assertEqual((sheet['B22'].value, sheet['G22'].value), ('Petugas Onduty', None))  # Mengetahui: by hand.
        self.assertEqual((sheet['B23'].value, sheet['G23'].value), ('NIP. 111', None))
        self.assertEqual([sheet[f'{column}22'].border.bottom.style for column in 'GHI'], ['thin'] * 3)  # Signature line.
        self.assertEqual(len(sheet._images), 2)

    def test_map_pdf(self, *mocks):
        report = self.create_report()

        response = self.client.get(reverse('api:daily_report:record_map_pdf', args=[report.pk]))

        self.assertEqual(response['Content-Disposition'], 'inline; filename=PetaHarian_2026-09-07.pdf')
        self.assertEqual(len(PdfReader(io.BytesIO(response.content)).pages), 1)

    @skipUnless(shutil.which('soffice') or shutil.which('libreoffice'), 'LibreOffice is not installed')
    def test_report_pdf_is_the_map_page_then_the_pde(self, *mocks):
        report = self.create_report()

        response = self.client.get(reverse('api:daily_report:record_pdf', args=[report.pk]))

        self.assertEqual(response['Content-Disposition'], 'inline; filename=Daily_Report_2026-09-07.pdf')
        pages = [page.extract_text() or '' for page in PdfReader(io.BytesIO(response.content)).pages]
        self.assertEqual(pages[0].strip(), '')                      # Peta Harian (an image).
        self.assertIn('Preliminary Determination', pages[1])        # PDE.

    def test_duty_summary_lists_the_report_in_the_pagi_duty_of_the_next_day(self, *mocks):
        report = self.create_report()

        data = self.client.get(reverse('api:duty_summary'), {'date': '2026-09-08', 'shift': 'P'}).json()
        daily, = [job for job in data['slots'][0]['jobs'] if job['key'] == 'daily-report']
        self.assertEqual([record['code'] for record in daily['records']], [report.report_id])

    def test_deleting_the_report_removes_its_map(self, *mocks):
        report = self.create_report()

        self.client.post(reverse('daily_report:dailyreport_delete_direct', args=[report.pk]))

        self.assertFalse(DailyReport.objects.exists())
        self.assertFalse(report.map_path.exists())

    def test_rekap_export_without_forms(self, *mocks):
        response = self.client.get(reverse('api:duty_summary_pdf'), {'date': '2026-01-01', 'shift': 'P'})

        self.assertEqual(response.status_code, 404)

    @skipUnless(shutil.which('soffice') or shutil.which('libreoffice'), 'LibreOffice is not installed')
    def test_rekap_export_merges_the_forms_in_print_order(self, *mocks):
        self.create_report()
        events = 'Date,OT (UTC),Lat\n2026-09-08,01:00:00,1.5\n'
        QcRecord.objects.create(
            qc_id='QC-2026-09-08-2P', date=datetime.date(2026, 9, 8), shift=Shift.PAGI, kelompok=2, kel_sebelum=1,
            operator=self.officer, jam_pelaksanaan=datetime.time(8, 0), qc_prev=events, qc=events,
        )

        response = self.client.get(reverse('api:duty_summary_pdf'), {'date': '2026-09-08', 'shift': 'P'})

        self.assertEqual(response.status_code, 200)
        pages = [page.extract_text() or '' for page in PdfReader(io.BytesIO(response.content)).pages]
        self.assertEqual(pages[0].strip(), '')                      # Peta Harian (an image).
        self.assertIn('Preliminary Determination', pages[1])        # PDE.
        self.assertIn('Petugas Onduty', pages[-1])                   # QC-3 signed by the officer.
        self.assertIn('Rekap_Dinas_2026-09-08_P', response['Content-Disposition'])
