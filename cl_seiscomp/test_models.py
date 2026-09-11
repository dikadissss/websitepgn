from django.test import TestCase

from core.models import Operator

from .models import CsRecordModel, StationListModel


class CsRecordModelSaveTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        StationListModel.objects.bulk_create(
            StationListModel(network='IA', code=code, province='P', location='L', digitizer_type='T', UPT='U')
            for code in ('AAI', 'BBJI')
        )
        cls.operator = Operator.objects.create(name='Operator CS', NIP='1')

    def test_station_lists_keep_known_codes_and_are_counted(self):
        record = CsRecordModel.objects.create(
            cs_id='CS-2025-11-10-2P', operator=self.operator, gaps='aai\nXXXX\n bbji ', spikes='', blanks=None,
        )

        self.assertEqual((record.gaps, record.count_gaps), ('AAI\nBBJI', 2))
        self.assertEqual((record.count_spikes, record.count_blanks), (0, 0))

    def test_emptied_list_resets_its_count(self):
        record = CsRecordModel.objects.create(cs_id='CS-2025-11-10-3S', operator=self.operator, gaps='AAI')
        record.gaps = ''
        record.save()

        self.assertEqual(record.count_gaps, 0)
