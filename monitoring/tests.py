import datetime
import io
import shutil
from unittest import skipUnless

import openpyxl
from django.test import TestCase
from django.urls import reverse
from pypdf import PdfReader

from core.models import Operator

from .models import ChecklistItem, ChecklistSection, DeviceAnswer, DeviceRecord, EmailWebRecord
from .reports import CHECK, CHECKED, UNCHECKED, build_workbook

HAS_LIBREOFFICE = shutil.which('soffice') or shutil.which('libreoffice')


def sheet_values(sheet):
    return {cell.coordinate: cell.value for row in sheet.iter_rows() for cell in row if cell.value is not None}


def contains(values, text):
    return any(text in str(value) for value in values.values())


class MonitoringTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.analyst = Operator.objects.create(name='Sigit Ariwibowo', NIP='333')

    def header(self, **values):
        return {'date': '2026-09-11', 'shift': 'Pagi', 'kelompok': 2, 'operator': self.analyst.pk,
                'check_time': '10:25', **values}

    def items(self, form):
        return list(ChecklistItem.objects.filter(section__form=form))

    def test_the_catalog_follows_the_2026_templates_without_credentials(self):
        counts = {section.key: section.items.count() for section in ChecklistSection.objects.all()}
        self.assertEqual(counts, {'email': 5, 'web-nasional': 7, 'web-internasional': 9, 'seiscomp': 3,
                                  'toast': 2, 'diseminasi': 2, 'tsp': 2, 'wrs': 1})
        self.assertFalse(ChecklistItem.objects.exclude(password='').exists())
        email = ChecklistSection.objects.get(key='email')
        self.assertTrue(email.heading.startswith('A. CEK EMAIL'))
        self.assertIn('Akbar', email.note)
        self.assertIn('tntmon', ChecklistItem.objects.get(name='Web Ina TnT').address)

    def test_create_email_web_checklist(self):
        email, *_ = self.items(ChecklistSection.Form.EMAIL_WEB)
        data = self.header(**{f'access_i{email.pk}': 'Y', f'info_i{email.pk}': 'Buletin PTWC',
                              f'confirmed_i{email.pk}': 'J', f'forward_to_i{email.pk}': 'pgn@bmkg.go.id'})

        response = self.client.post(reverse('monitoring:email_web_create'), data)

        self.assertRedirects(response, reverse('monitoring:email_web_list'))
        record = EmailWebRecord.objects.get()
        self.assertEqual((record.ew_id, record.check_time), ('EW-2026-09-11-2P', datetime.time(10, 25)))
        self.assertEqual(record.answers.count(), len(self.items(ChecklistSection.Form.EMAIL_WEB)))
        answer = record.answers.get(item=email)
        self.assertEqual((answer.access, answer.info, answer.confirmed, answer.forward_to, answer.item_name),
                         ('Y', 'Buletin PTWC', 'J', 'pgn@bmkg.go.id', 'Inartsp'))
        self.assertEqual(record.answers.exclude(item=email).exclude(access='').count(), 0)

    def test_invalid_choices_are_not_stored(self):
        web = ChecklistItem.objects.filter(section__key='web-nasional').first()
        self.client.post(reverse('monitoring:email_web_create'),
                         self.header(**{f'access_i{web.pk}': 'X', f'confirmed_i{web.pk}': 'J'}))

        answer = EmailWebRecord.objects.get().answers.get(item=web)
        self.assertEqual((answer.access, answer.confirmed), ('', ''))  # A web answer is B/BB, not J.

    def test_one_checklist_per_duty(self):
        self.client.post(reverse('monitoring:device_create'), self.header())

        response = self.client.post(reverse('monitoring:device_create'), self.header(kelompok=3))

        self.assertContains(response, 'DC-2026-09-11-2P sudah ada')
        self.assertEqual(DeviceRecord.objects.count(), 1)

    def test_update_keeps_the_items_as_they_were_checked(self):
        self.client.post(reverse('monitoring:device_create'), self.header())
        record = DeviceRecord.objects.get()
        first = record.answers.first()
        ChecklistItem.objects.filter(pk=first.item_id).update(name='Nama baru di katalog')

        self.client.post(reverse('monitoring:device_update', args=[record.pk]),
                         self.header(**{f'ok_a{first.pk}': 'tidak'}))

        answer = DeviceAnswer.objects.get(record=record, item_id=first.item_id)
        self.assertEqual((answer.ok, answer.item_name), (False, first.item_name))
        self.assertEqual(record.answers.count(), 10)

    def test_device_workbook(self):
        seiscomp = ChecklistItem.objects.filter(section__key='seiscomp').order_by('order')
        wrs = ChecklistItem.objects.get(section__key='wrs')
        wrs.password = 'rahasia'
        wrs.save()
        self.client.post(reverse('monitoring:device_create'),
                         self.header(**{f'ok_i{seiscomp[0].pk}': 'ya', f'ok_i{seiscomp[1].pk}': 'tidak'}))

        sheet = build_workbook(DeviceRecord.objects.get()).active
        values = sheet_values(sheet)

        self.assertEqual(values['A1'], DeviceRecord.title)
        self.assertTrue(values['A3'].startswith('Kelompok') and values['A3'].endswith(': II (Dua)'))
        self.assertTrue(values['C4'].startswith('Hari/Tanggal (Checklist)'))
        self.assertTrue(values['C4'].endswith(': Jumat, 11 September 2026'))
        self.assertTrue(values['C5'].endswith(': 10:25 WIB'))
        self.assertEqual(values['A8'], 'MONITORING SeisComP (Meja D6, Client 2)')
        marks = [coordinate for coordinate, value in values.items() if value == CHECK]
        self.assertEqual([coordinate[0] for coordinate in marks], ['C', 'D'])  # Ya, then Tidak.
        self.assertTrue(contains(values, 'Password: rahasia'))
        self.assertIn('Pejabat On Duty', values.values())
        self.assertIn('Sigit Ariwibowo', values.values())
        self.assertEqual((sheet.page_setup.fitToWidth, sheet.page_setup.fitToHeight), (1, 1))

    def test_email_workbook(self):
        email = ChecklistItem.objects.filter(section__key='email').order_by('order').first()
        email.password = 'secret-1'
        email.save()
        self.client.post(reverse('monitoring:email_web_create'),
                         self.header(**{f'access_i{email.pk}': 'Y', f'confirmed_i{email.pk}': 'J'}))

        sheet = build_workbook(EmailWebRecord.objects.get()).active
        values = sheet_values(sheet)

        row = next(int(coordinate[1:]) for coordinate, value in values.items()
                   if value == 'username : inartsp@bmkg.go.id')
        self.assertEqual(values[f'D{row + 1}'], 'password : secret-1')  # The password comes from the catalog.
        self.assertEqual((values[f'E{row}'], values[f'E{row + 1}']), (f'Y {CHECKED}', f'N {UNCHECKED}'))
        self.assertEqual((values[f'G{row}'], values[f'G{row + 1}']), (f'J {CHECKED}', f'BJ {UNCHECKED}'))
        self.assertTrue(values[f'C{row}'].startswith('Kelima email ini tergabung'))
        self.assertTrue(contains(values, 'A. CEK EMAIL'))
        self.assertIn('Web Nasional', values.values())
        self.assertTrue(contains(values, 'Admin Web BNPB = Leonard'))
        self.assertTrue(contains(values, 'tntmon/datastatus.php'))
        self.assertIn('Pejabat on Duty', values.values())

    def test_both_checklists_are_duty_jobs(self):
        self.client.post(reverse('monitoring:email_web_create'), self.header())
        self.client.post(reverse('monitoring:device_create'), self.header())

        data = self.client.get(reverse('api:duty_summary'), {'date': '2026-09-11', 'shift': 'P'}).json()

        codes = {job['key']: [record['code'] for record in job['records']] for job in data['slots'][0]['jobs']}
        self.assertEqual((codes['email-web'], codes['device-checklist']), (['EW-2026-09-11-2P'], ['DC-2026-09-11-2P']))
        response = self.client.get(reverse('api:email_web:record_xlsx', args=[EmailWebRecord.objects.get().pk]))
        self.assertEqual(openpyxl.load_workbook(io.BytesIO(response.content)).active['A1'].value, EmailWebRecord.title)

    @skipUnless(HAS_LIBREOFFICE, 'LibreOffice is not installed')
    def test_pdf_on_one_page(self):
        self.client.post(reverse('monitoring:device_create'), self.header())
        self.client.post(reverse('monitoring:email_web_create'), self.header())

        for name, model, title in (('device_checklist', DeviceRecord, 'Checklist SeisComP'),
                                   ('email_web', EmailWebRecord, 'MONITORING EMAIL')):
            response = self.client.get(reverse(f'api:{name}:record_pdf', args=[model.objects.get().pk]))
            pages = PdfReader(io.BytesIO(response.content)).pages
            self.assertEqual(len(pages), 1, name)
            self.assertIn(title, pages[0].extract_text())
