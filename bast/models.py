import datetime

from django.db import models

from core.choices import GROUP_CHOICES
from core.models import DutyRecord, Operator

WAKTU_PELAKSANAAN = (
    ('08:00 - 14:00 WIB', '08:00 - 14:00 WIB'),
    ('14:00 - 20:00 WIB', '14:00 - 20:00 WIB'),
    ('20:00 - 02:00 WIB', '20:00 - 02:00 WIB'),
    ('02:00 - 08:30 WIB', '02:00 - 08:30 WIB'),
)

WAKTU_CS = (
    ('00:00 WIB', '00:00 WIB'),
    ('06:00 WIB', '06:00 WIB'),
    ('12:00 WIB', '12:00 WIB'),
    ('18:00 WIB', '18:00 WIB'),
)


def get_default_poco_exp():
    return datetime.date(2026, 1, 17)


def get_default_samsung_exp():
    return datetime.date(2037, 12, 31)


class BastRecordModel(DutyRecord):
    code_field = 'bast_id'

    # The officer who made this BAST; not necessarily the SPV or one of the members.
    # Nullable only because BASTs made before this field existed have no officer recorded.
    operator = models.ForeignKey(
        Operator, on_delete=models.PROTECT, null=True, blank=True, related_name='bast_records',
    )
    bast_id = models.CharField(max_length=18, default='0', unique=True)
    waktu_pelaksanaan = models.CharField(choices=WAKTU_PELAKSANAAN, max_length=20, default='08:00 - 14:00 WIB', blank=True, null=True)
    kel_berikut = models.PositiveSmallIntegerField(choices=GROUP_CHOICES, default=1)
    events = models.TextField(default='0')
    spv = models.ForeignKey(Operator, on_delete=models.PROTECT)
    NIP = models.CharField(max_length=18, default='0', blank=True)
    event_indonesia = models.IntegerField(default=0)
    event_luar = models.IntegerField(default=0)
    event_dirasakan = models.IntegerField(default=0)
    event_dikirim = models.IntegerField(default=0)
    member = models.TextField(max_length=1000, default='')  # JSON list of {"nama", "keterangan"}.
    count_gaps = models.IntegerField(default=0)
    count_spikes = models.IntegerField(default=0)
    count_blanks = models.IntegerField(default=0)
    waktu_cs = models.CharField(choices=WAKTU_CS, max_length=20, default='00:00 WIB', blank=True, null=True)
    pulsa_poco = models.IntegerField(default=0)
    poco_exp = models.DateField(default=get_default_poco_exp)
    samsung_exp = models.DateField(default=get_default_samsung_exp)
    notes = models.TextField(max_length=1000, default='', blank=True, null=True)
