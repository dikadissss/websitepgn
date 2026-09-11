"""Choices and defaults shared by every duty record (BAST, QC, QCFM, Checklist SeisComP)."""
import datetime

from django.db import models
from django.utils import timezone


class Shift(models.TextChoices):
    PAGI = 'Pagi', 'Pagi'
    SIANG = 'Siang', 'Siang'
    MALAM = 'Malam', 'Malam'
    DINI_HARI = 'Dini Hari', 'Dini Hari'


GROUP_CHOICES = [(number, number) for number in range(1, 7)]

# Duty slot codes (P, S, M1, M2) -> (shift, day offset of the record date).
# M2 (dini hari, 02:00-08:30) continues the M1 duty of the same group, so it is
# stored with the next calendar date: M2 of 2025-11-10 is the "*-2025-11-11-1D" record.
SHIFT_CODES = {
    'P': (Shift.PAGI, 0),
    'S': (Shift.SIANG, 0),
    'M1': (Shift.MALAM, 0),
    'M2': (Shift.DINI_HARI, 1),
}


def resolve_duty_slot(date, code):
    """Return the (record_date, shift) pair holding the records of a duty slot."""
    shift, day_offset = SHIFT_CODES[code]
    return date + datetime.timedelta(days=day_offset), shift


def local_today():
    return timezone.localdate()


def local_time_now():
    return timezone.localtime().time().replace(second=0, microsecond=0)
