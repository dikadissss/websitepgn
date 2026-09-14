from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.messages import get_messages
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from .models import CsRecordModel, StationListModel
from .reports import build_workbook
from core.models import Operator
from daily_report.tests import solid_tile
from slmon.models import SlmonSnapshot
from django.contrib.auth.models import User
from pathlib import Path
from unittest import mock
import io
import shutil
import tempfile


class StationBulkCreateViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.operator = Operator.objects.create(name='Test Operator', NIP='1234567890')
        self.url = reverse('cl_seiscomp:sl_bulk_create')
        
    def test_valid_csv_file_upload(self):
        """Test successful bulk station creation with valid CSV file"""
        csv_content = b"network,code,province,location,digitizer_type,UPT,longitude,latitude\nNET1,ST01,Province1,Location1,Type1,UPT1,106.123,-6.456\nNET2,ST02,Province2,Location2,Type2,UPT2,107.789,-7.123"
        csv_file = SimpleUploadedFile("stations.csv", csv_content, content_type="text/csv")
        
        response = self.client.post(self.url, {'csv_file': csv_file})
        
        self.assertEqual(response.status_code, 302)  # Redirect after success
        self.assertEqual(StationListModel.objects.count(), 2)
        
        station1 = StationListModel.objects.get(code='ST01')
        self.assertEqual(station1.network, 'NET1')
        self.assertEqual(station1.longitude, 106.123)
        
    def test_valid_csv_data_paste(self):
        """Test successful bulk station creation with pasted CSV data"""
        csv_data = "NET1,ST01,Province1,Location1,Type1,UPT1,106.123,-6.456\nNET2,ST02,Province2,Location2,Type2,UPT2,107.789,-7.123"
        
        response = self.client.post(self.url, {'csv_data': csv_data})
        
        self.assertEqual(response.status_code, 302)  # Redirect after success
        self.assertEqual(StationListModel.objects.count(), 2)
        
    def test_invalid_longitude_latitude_types(self):
        """Test handling of invalid longitude/latitude data types"""
        csv_data = "NET1,ST01,Province1,Location1,Type1,UPT1,invalid_lon,invalid_lat"
        
        response = self.client.post(self.url, {'csv_data': csv_data})
        
        # Should handle error gracefully, not return 500
        self.assertNotEqual(response.status_code, 500)
        self.assertEqual(StationListModel.objects.count(), 0)
        
    def test_missing_csv_columns(self):
        """Test handling of CSV rows with missing columns"""
        csv_data = "NET1,ST01,Province1"  # Missing 5 columns
        
        response = self.client.post(self.url, {'csv_data': csv_data})
        
        # Should handle error gracefully, not return 500
        self.assertNotEqual(response.status_code, 500)
        self.assertEqual(StationListModel.objects.count(), 0)
        
    def test_empty_csv_rows(self):
        """Test handling of empty CSV rows"""
        csv_data = "NET1,ST01,Province1,Location1,Type1,UPT1,106.123,-6.456\n\n\nNET2,ST02,Province2,Location2,Type2,UPT2,107.789,-7.123"
        
        response = self.client.post(self.url, {'csv_data': csv_data})
        
        # Should handle empty rows gracefully
        self.assertNotEqual(response.status_code, 500)
        self.assertEqual(StationListModel.objects.count(), 2)
        
    def test_no_csv_file_or_data(self):
        """Test error handling when no CSV file or data is provided"""
        response = self.client.post(self.url, {})
        
        self.assertEqual(response.status_code, 302)  # Redirect with error message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('Please upload a CSV file or provide CSV data' in str(m) for m in messages))
        
    def test_invalid_file_extension(self):
        """Test error handling for non-CSV files"""
        txt_file = SimpleUploadedFile("stations.txt", b"some content", content_type="text/plain")
        
        response = self.client.post(self.url, {'csv_file': txt_file})
        
        self.assertEqual(response.status_code, 302)  # Redirect with error message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('This is not a CSV file' in str(m) for m in messages))


@mock.patch('daily_report.maps.fetch_tile', side_effect=solid_tile)
class ChecklistSlmonTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.operator = Operator.objects.create(name='Petugas Ceklis', NIP='333')

    def setUp(self):
        media, tiles = tempfile.mkdtemp(), tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, media)
        self.addCleanup(shutil.rmtree, tiles)
        settings_override = override_settings(MEDIA_ROOT=media, TILE_CACHE_DIR=tiles)
        settings_override.enable()
        self.addCleanup(settings_override.disable)
        self.snapshot = SlmonSnapshot.objects.create(data_time=timezone.now(), stations=[
            ['IA', 'AAI', 128.19, -3.69, 'green', 'green'], ['IA', 'BBB', 110.0, -7.0, 'grey', 'black'],
        ])

    def form_data(self, **values):
        return {
            'kelompok': 1, 'date': '2026-09-11', 'shift': 'Pagi', 'jam_pelaksanaan': '12:00 WIB',
            'operator': self.operator.pk, 'cs_id': 'CS-2026-09-11-2P', 'gaps': '', 'spikes': '', 'blanks': '',
            'slmon': 1, **values,
        }

    def create_with_snapshot(self):
        response = self.client.post(reverse('cl_seiscomp:cs_create'), self.form_data(slmon_snapshot_id=self.snapshot.pk))
        self.assertRedirects(response, reverse('cl_seiscomp:cs_list'))
        return CsRecordModel.objects.get()

    def test_the_checklist_keeps_its_own_copy_of_the_slmon_map(self, _):
        record = self.create_with_snapshot()
        image_path = Path(record.slmon_image.path)
        self.assertEqual(record.slmon, 1)
        self.assertTrue(record.slmon_image.name.startswith('cl_seiscomp/slmon_images/slmon_CS-2026-09-11-2P'))
        self.assertEqual(image_path.read_bytes(), self.snapshot.monitor_map_path.read_bytes())  # The slmon2 view.

        self.snapshot.delete()
        self.client.post(reverse('cl_seiscomp:cs_update', args=[record.pk]), self.form_data(slmon=5))

        record.refresh_from_db()
        self.assertEqual((record.slmon, Path(record.slmon_image.path)), (5, image_path))
        self.assertTrue(image_path.exists())
        sheet = build_workbook(record)['slmon']
        image, = sheet._images
        # Centered under the title (A1:P1): 16 columns of 109 px as LibreOffice lays them out, the map 1300 x 626 px.
        self.assertEqual((image.anchor._from.col, image.width, image.height), (2, 1300, 626))
        self.assertEqual((sheet['C24'].value, sheet['C37'].value), (None, 'Petugas on Duty,'))  # Moved below the map.
        self.assertEqual(sheet['C41'].value, 'Petugas Ceklis')
        self.assertTrue(sheet.print_options.horizontalCentered)

    @mock.patch('slmon.services.fetch_status')
    def test_the_checklist_takes_a_preview_without_storing_a_snapshot(self, fetch_status, _):
        from slmon.services import preview_path
        from slmon.tests import STATUS
        fetch_status.return_value = STATUS
        SlmonSnapshot.objects.all().delete()
        form = self.client.get(reverse('cl_seiscomp:cs_create'))
        self.assertContains(form, 'id="slmon_status"')
        self.assertContains(form, reverse('api:slmon:preview'))
        self.assertNotContains(form, 'slmon_map_style')  # Only the slmon2 view, no Peta to choose.

        preview = self.client.post(reverse('api:slmon:preview')).json()
        path = preview_path(preview['id'].removeprefix('preview-'))
        slmon2 = path.read_bytes()
        response = self.client.post(reverse('cl_seiscomp:cs_create'), self.form_data(slmon_snapshot_id=preview['id']))

        self.assertRedirects(response, reverse('cl_seiscomp:cs_list'))
        record = CsRecordModel.objects.get()
        self.assertEqual(Path(record.slmon_image.path).read_bytes(), slmon2)
        self.assertFalse(SlmonSnapshot.objects.exists())
        self.assertFalse(path.exists())  # Copied, so the preview is gone.

    def test_an_invalid_preview_is_ignored(self, _):
        response = self.client.post(reverse('cl_seiscomp:cs_create'),
                                    self.form_data(slmon_snapshot_id='preview-../../x'))

        self.assertRedirects(response, reverse('cl_seiscomp:cs_list'))
        self.assertFalse(CsRecordModel.objects.get().slmon_image)

    def test_clearing_the_slmon_image(self, _):
        record = self.create_with_snapshot()
        image_path = Path(record.slmon_image.path)

        self.client.post(reverse('cl_seiscomp:cs_update', args=[record.pk]), self.form_data(clear_image='on'))

        record.refresh_from_db()
        self.assertFalse(record.slmon_image)
        self.assertFalse(image_path.exists())

    def test_checklist_prints_columns_a_to_r_at_one_page_width(self, _):
        record = CsRecordModel.objects.create(cs_id='CS-2026-09-11-2P', date=timezone.localdate(), shift='Pagi',
                                              kelompok=1, operator=self.operator)

        sheet = build_workbook(record)['Checklist Seiscomp']

        self.assertTrue(sheet.print_area.endswith('$A$1:$R$287'))
        self.assertTrue(sheet.sheet_properties.pageSetUpPr.fitToPage)
        self.assertEqual((sheet.page_setup.fitToWidth, sheet.page_setup.fitToHeight), (1, 0))
