from django.db import models

from core.choices import GROUP_CHOICES, local_time_now
from core.models import DutyRecord


class QcFmRecord(DutyRecord):
    code_field = 'qcfm_id'

    qcfm_id = models.CharField(max_length=18, default='0', unique=True)
    jam_pelaksanaan = models.TimeField(default=local_time_now)
    qcfm_prev = models.TextField(default='0')
    qcfm = models.TextField(default='0')
    NIP = models.CharField(max_length=18, default='0', blank=True, null=True)
    kel_sebelum = models.PositiveSmallIntegerField(choices=GROUP_CHOICES, default=1)
