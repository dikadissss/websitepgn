import datetime
import io
import shutil
from unittest import skipUnless

import openpyxl
from django.test import TestCase
from django.urls import reverse

from core.models import Operator

from .models import QcRecord

EVENTS_CSV = 'Date,OT (UTC),Lat\n2025-11-10,01:00:00,1.5\n2025-11-10,02:00:00,2.5\n'


class QcExportTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        operator = Operator.objects.create(name='Operator QC', NIP='123')
        cls.record = QcRecord.objects.create(
            qc_id='QC-2025-11-10-2P', date=datetime.date(2025, 11, 10), shift='Pagi', kelompok=2, kel_sebelum=1,
            operator=operator, jam_pelaksanaan=datetime.time(8, 0), qc_prev=EVENTS_CSV, qc=EVENTS_CSV,
        )

    def test_xlsx(self):
        response = self.client.get(reverse('api:qc:record_xlsx', args=[self.record.pk]))

        self.assertEqual(response['Content-Disposition'], 'attachment; filename=QC-2025-11-10-P.xlsx')
        sheet = openpyxl.load_workbook(io.BytesIO(response.content)).active
        self.assertEqual((sheet['G2'].value, sheet['G3'].value, sheet['G5'].value), (': 10 November 2025', ': Senin', ': Kel. 2'))
        # Event columns start at C, so with three columns the row label lands in F.
        self.assertEqual(sheet['F8'].value, 'Kel. 1')  # Previous group's row of the first event.
        self.assertEqual(sheet['F9'].value, 'QC')      # This group's QC row of the first event.
        # Two events take four rows from row 8; the signature is 8 rows below them.
        self.assertEqual(sheet.cell(row=20, column=13).value, 'Operator QC')

    def test_csv_export_streams_every_record(self):
        response = self.client.get(reverse('api:qc:record_csv'))
        content = b''.join(response.streaming_content).decode()

        self.assertTrue(content.startswith('﻿"QC ID","Date"'))
        self.assertIn('"QC-2025-11-10-2P","2025-11-10","08:00:00","Pagi","2","1","Operator QC"', content)

    @skipUnless(shutil.which('soffice') or shutil.which('libreoffice'), 'LibreOffice is not installed')
    def test_pdf(self):
        response = self.client.get(reverse('api:qc:record_pdf', args=[self.record.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content.startswith(b'%PDF'))
