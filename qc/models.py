from django.db import models

from core.choices import GROUP_CHOICES, local_time_now
from core.models import DutyRecord


class QcRecord(DutyRecord):
    code_field = 'qc_id'

    qc_id = models.CharField(max_length=16, default='0', unique=True)
    jam_pelaksanaan = models.TimeField(default=local_time_now)
    qc_prev = models.TextField(default='0')
    qc = models.TextField(default='0')
    NIP = models.CharField(max_length=18, default='0')
    event_indonesia = models.IntegerField(default=0)
    event_luar = models.IntegerField(default=0)
    kel_sebelum = models.PositiveSmallIntegerField(choices=GROUP_CHOICES, default=1)


class ErrorStation(models.Model):
    kode_stasiun = models.CharField(max_length=20, unique=True)
    lokasi = models.CharField(max_length=200, null=True, blank=True)
    deskripsi_error = models.TextField(blank=True)

    def __str__(self):
        return f"{self.kode_stasiun} - {self.lokasi}"
