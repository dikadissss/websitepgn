import datetime

import pandas as pd
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from cl_seiscomp.models import CsRecordModel
from qc.models import QcRecord

from . import regions
from .choices import Shift, resolve_duty_slot
from .models import Kelompok, Operator

DAY = datetime.date(2025, 11, 10)
NEXT_DAY = datetime.date(2025, 11, 11)


class NtwcRegionTests(SimpleTestCase):
    def test_polygon_file(self):
        polygon, = regions.ntwc_polygons()
        self.assertEqual(len(polygon), 90)

    def test_events_inside_and_outside_indonesia(self):
        self.assertTrue(regions.in_indonesia(106.8, -6.2))    # Jakarta
        self.assertTrue(regions.in_indonesia(121.5, -8.4))    # Flores
        self.assertFalse(regions.in_indonesia(143.9, 12.0))   # Mariana Islands
        self.assertFalse(regions.in_indonesia(100.5, 13.7))   # Bangkok

    def test_count_indonesia(self):
        table = pd.DataFrame({'Lat': ['8.12901 S', '12.0 N'], 'Long': ['120.43388 E', '143.9 E']})

        self.assertEqual(regions.count_indonesia(table), (1, 1))


class ResolveDutySlotTests(SimpleTestCase):
    def test_day_and_evening_duties_keep_the_date(self):
        self.assertEqual(resolve_duty_slot(DAY, 'P'), (DAY, Shift.PAGI))
        self.assertEqual(resolve_duty_slot(DAY, 'S'), (DAY, Shift.SIANG))
        self.assertEqual(resolve_duty_slot(DAY, 'M1'), (DAY, Shift.MALAM))

    def test_m2_is_the_dini_hari_record_of_the_next_date(self):
        self.assertEqual(resolve_duty_slot(DAY, 'M2'), (NEXT_DAY, Shift.DINI_HARI))


class KelompokTests(TestCase):
    def setUp(self):
        self.operator1 = Operator.objects.create(name="Test Operator 1", NIP="1234567890123456")
        self.operator2 = Operator.objects.create(name="Test Operator 2", NIP="2345678901234567")
        self.kelompok = Kelompok.objects.create(name=1)
        self.kelompok.set_members([self.operator2.pk, self.operator1.pk])

    def test_update_view_passes_existing_members_in_order(self):
        response = self.client.get(reverse('core:kelompok_update', kwargs={'pk': self.kelompok.pk}))

        self.assertEqual(response.context['existing_members'], [str(self.operator2.pk), str(self.operator1.pk)])
        self.assertContains(response, 'existingMemberIds')
        self.assertContains(response, f"'{self.operator1.pk}'")

    def test_create_view_has_empty_existing_members(self):
        response = self.client.get(reverse('core:kelompok_create'))

        self.assertContains(response, 'existingMemberIds = []')

    def test_saving_the_form_keeps_the_member_order(self):
        response = self.client.post(
            reverse('core:kelompok_update', kwargs={'pk': self.kelompok.pk}),
            {'name': 1, 'member': f'{self.operator1.pk},{self.operator2.pk}'},
        )

        self.assertRedirects(response, reverse('core:kelompok_list'))
        self.assertEqual(self.kelompok.ordered_members(), [self.operator1, self.operator2])

    def test_unknown_member_is_rejected(self):
        response = self.client.post(reverse('core:kelompok_create'), {'name': 2, 'member': '999999'})

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Kelompok.objects.filter(name=2).exists())

    def test_group_members_api_keeps_the_order(self):
        response = self.client.get(reverse('api:group_members', args=[1]))

        self.assertEqual([member['id'] for member in response.json()['members']], [self.operator2.pk, self.operator1.pk])


class DutyRecordApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.ani = Operator.objects.create(name='Ani', NIP='1')
        cls.budi = Operator.objects.create(name='Budi', NIP='2')
        for operator, code, date, shift, group in (
            (cls.ani, 'QC-2025-11-10-2P', DAY, Shift.PAGI, 2),
            (cls.budi, 'QC-2025-11-10-4M', DAY, Shift.MALAM, 1),
            (cls.budi, 'QC-2025-11-11-1D', NEXT_DAY, Shift.DINI_HARI, 1),
            (cls.ani, 'QC-2025-11-11-2P', NEXT_DAY, Shift.PAGI, 3),
        ):
            QcRecord.objects.create(qc_id=code, date=date, shift=shift, kelompok=group, operator=operator)
        CsRecordModel.objects.create(cs_id='CS-2025-11-11-1D', date=NEXT_DAY, shift=Shift.DINI_HARI, kelompok=1, operator=cls.ani)

    def records(self, **params):
        response = self.client.get(reverse('api:qc:record_list'), params)
        self.assertEqual(response.status_code, 200)
        return response.json()

    def test_filters_by_group_and_operator(self):
        self.assertEqual([row['code'] for row in self.records(group=1)], ['QC-2025-11-11-1D', 'QC-2025-11-10-4M'])
        self.assertEqual({row['code'] for row in self.records(operator=self.ani.pk)}, {'QC-2025-11-10-2P', 'QC-2025-11-11-2P'})

    def test_shift_code_and_date_select_the_duty_slot(self):
        self.assertEqual([row['code'] for row in self.records(date='2025-11-10', shift='M2')], ['QC-2025-11-11-1D'])

    def test_tabulator_page_with_sorting(self):
        page = self.records(page=1, size=3, **{'sort[0][field]': 'code', 'sort[0][dir]': 'asc'})

        self.assertEqual((page['last_page'], page['last_row']), (2, 4))
        self.assertEqual([row['code'] for row in page['data']], ['QC-2025-11-10-2P', 'QC-2025-11-10-4M', 'QC-2025-11-11-1D'])
        self.assertEqual(page['data'][0]['operator_name'], 'Ani')

    def test_search_filter(self):
        page = self.records(page=1, **{'filter[0][field]': 'search', 'filter[0][type]': 'like', 'filter[0][value]': 'budi'})

        self.assertEqual(page['last_row'], 2)

    def test_invalid_parameters_are_bad_requests(self):
        self.assertEqual(self.client.get(reverse('api:qc:record_list'), {'group': 'x'}).status_code, 400)
        self.assertEqual(self.client.get(reverse('api:qc:record_list'), {'filter[0][field]': 'secret'}).status_code, 400)

    def test_stats_per_group_and_per_operator(self):
        by_group = self.client.get(reverse('api:qc:record_stats'), {'by': 'group'}).json()
        by_operator = self.client.get(reverse('api:qc:record_stats'), {'by': 'operator', 'group': 1}).json()

        self.assertEqual(by_group['data'], [{'group': 1, 'count': 2}, {'group': 2, 'count': 1}, {'group': 3, 'count': 1}])
        self.assertEqual(by_operator['data'], [{'operator_id': self.budi.pk, 'operator_name': 'Budi', 'count': 2}])

    def test_duty_summary_of_m2_reads_the_next_date(self):
        data = self.client.get(reverse('api:duty_summary'), {'date': '2025-11-10', 'shift': 'M2', 'group': 1}).json()

        slot, = data['slots']
        self.assertEqual(slot['record_date'], '2025-11-11')
        self.assertEqual(
            {job['key']: [record['code'] for record in job['records']] for job in slot['jobs']},
            {'bast': [], 'qc': ['QC-2025-11-11-1D'], 'qcfm': [], 'seiscomp-checklist': ['CS-2025-11-11-1D'],
             'tide-gauge': [], 'email-web': [], 'device-checklist': []},
        )

    def test_duty_summary_without_shift_lists_the_four_duties(self):
        data = self.client.get(reverse('api:duty_summary'), {'date': '2025-11-10'}).json()

        self.assertEqual([slot['shift_code'] for slot in data['slots']], ['P', 'S', 'M1', 'M2'])

    def test_daily_report_is_a_job_of_the_pagi_duty_only(self):
        data = self.client.get(reverse('api:duty_summary'), {'date': '2025-11-10'}).json()

        self.assertEqual(
            {slot['shift_code']: 'daily-report' in [job['key'] for job in slot['jobs']] for slot in data['slots']},
            {'P': True, 'S': False, 'M1': False, 'M2': False},
        )

    def test_operator_with_records_is_not_deleted(self):
        response = self.client.post(reverse('core:operator_delete_direct', args=[self.ani.pk]), follow=True)

        self.assertTrue(Operator.objects.filter(pk=self.ani.pk).exists())
        self.assertContains(response, 'tidak bisa dihapus')

    def test_rekap_page(self):
        response = self.client.get(reverse('rekap'))

        self.assertContains(response, 'Rekap Dinas')
        self.assertContains(response, reverse('api:qc:record_stats'))
