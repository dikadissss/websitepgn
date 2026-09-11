import datetime
import io
from unittest import mock

import openpyxl
from django.test import TestCase
from django.urls import reverse

from core.models import Operator

from .forms import BastRecordForm
from .models import BastRecordModel

FEED = (
    " List of real time automatic BMKG earthquake locations\n"
    " ....................................................\n"
    " | Origin Time (GMT)   | Status    |cntP |Mag  |TypeMag |cntM |AZgap| RMS |Lat      | Lon      | Depth  | Remarks\n"
    " ....................................................\n"
    " | 2025-11-10 08:00:00 | manual    | 30  | 3.1  | M      | 20 | 58  | 1.7 | 8.12901 S  | 120.43388 E | 10 km  | Flores Sea\n"
    " | 2025-11-10 09:00:00 | manual    | 30  | 5.5  | mb     | 20 | 58  | 1.7 | 12.0 N  | 143.9 E | 10 km  | Mariana Islands Region\n"
)


class BastOperatorTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.spv = Operator.objects.create(name='Supervisor', NIP='111')
        cls.officer = Operator.objects.create(name='Petugas Dinas', NIP='222')
        # Made before BASTs recorded their officer.
        cls.old_record = BastRecordModel.objects.create(
            bast_id='BAST-2025-11-10-2P', date=datetime.date(2025, 11, 10), shift='Pagi', kelompok=2, kel_berikut=2,
            spv=cls.spv, member='[{"nama": "Petugas Dinas", "keterangan": "Hadir"}, {"nama": "Lain", "keterangan": "Cuti"}]',
        )

    def form_data(self, **overrides):
        return {
            'date': '2025-11-10', 'bast_id': 'BAST-2025-11-10-3S', 'waktu_pelaksanaan': '14:00 - 20:00 WIB',
            'shift': 'Siang', 'kelompok': 2, 'kel_berikut': 3, 'spv': self.spv.pk, 'NIP': '111', 'events': '0',
            'event_indonesia': 0, 'event_luar': 0, 'event_dirasakan': 0, 'event_dikirim': 0, 'member': '[]',
            'count_gaps': 0, 'count_spikes': 0, 'count_blanks': 0, 'waktu_cs': '18:00 WIB', 'pulsa_poco': 0,
            'poco_exp': '2026-01-17', 'samsung_exp': '2037-12-31', 'notes': '',
            **overrides,
        }

    def test_new_bast_needs_its_officer(self):
        self.assertIn('operator', BastRecordForm(data=self.form_data()).errors)

        form = BastRecordForm(data=self.form_data(operator=self.officer.pk))
        self.assertTrue(form.is_valid(), form.errors)
        record = form.save()
        self.assertEqual((record.operator, record.spv), (self.officer, self.spv))

    def test_form_page_has_the_officer_select(self):
        response = self.client.get(reverse('bast:bastrecord_create'))

        self.assertContains(response, 'Petugas (pembuat BAST)')
        self.assertContains(response, 'name="operator"')

    def test_records_can_be_queried_by_officer_and_group(self):
        BastRecordModel.objects.create(
            bast_id='BAST-2025-11-10-3S', date=datetime.date(2025, 11, 10), shift='Siang', kelompok=2,
            spv=self.spv, operator=self.officer,
        )

        by_officer = self.client.get(reverse('api:bast:record_list'), {'operator': self.officer.pk}).json()
        by_group = self.client.get(reverse('api:bast:record_list'), {'group': 2}).json()
        self.assertEqual([row['code'] for row in by_officer], ['BAST-2025-11-10-3S'])
        self.assertEqual(len(by_group), 2)

    def test_old_bast_without_officer_is_listed_and_exported(self):
        row, = self.client.get(reverse('api:bast:record_list')).json()
        self.assertIsNone(row['operator_id'])
        self.assertEqual(row['supervisor_name'], 'Supervisor')

        response = self.client.get(reverse('api:bast:record_xlsx', args=[self.old_record.pk]))
        self.assertEqual(response.status_code, 200)
        sheet = openpyxl.load_workbook(io.BytesIO(response.content)).active
        self.assertEqual(sheet['J4'].value, 'II (Dua)')
        self.assertEqual((sheet['K9'].value, sheet['L10'].value), ('Petugas Dinas', 'Cuti'))
        self.assertEqual(sheet['L19'].value, '1')
        self.assertEqual(sheet['C55'].value, 'Supervisor')

    @mock.patch('core.feeds._download', return_value=FEED)
    def test_fetched_events_are_counted_inside_and_outside_the_ntwc_area(self, _download):
        data = self.client.get(reverse('api:bast:events'),
                               {'start': '2025-11-10 07:00:00', 'end': '2025-11-10 14:00:00'}).json()

        self.assertEqual(len(data['rows']), 2)
        self.assertEqual(data['counts'], {'indonesia': 1, 'abroad': 1})

    def test_latest_record_values(self):
        data = self.client.get(reverse('api:bast:record_latest')).json()

        self.assertEqual(data['code'], 'BAST-2025-11-10-2P')
        self.assertEqual(data['members'][0], {'nama': 'Petugas Dinas', 'keterangan': 'Hadir'})
        self.assertEqual((data['poco_expiry'], data['samsung_expiry']), ('2026-01-17', '2037-12-31'))
