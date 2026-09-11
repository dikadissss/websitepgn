"""Monitoring checklists of every duty: email, web and social media (EmailWebRecord), and the computers and
applications of the operation room (DeviceRecord).

What is checked comes from a catalog edited in the admin (ChecklistSection, ChecklistItem), so account passwords
live only in the database. Each record keeps its answers together with a copy of the item names, so later catalog
edits do not change what was checked."""
from django.db import models

from core.choices import Shift, local_time_now
from core.models import DutyRecord

SHIFT_SUFFIXES = {Shift.DINI_HARI: '1D', Shift.PAGI: '2P', Shift.SIANG: '3S', Shift.MALAM: '4M'}


def duty_code(prefix, date, shift):
    """'EW-2026-09-11-2P': the same shift suffixes as the codes of the other jobs."""
    return f'{prefix}-{date:%Y-%m-%d}-{SHIFT_SUFFIXES[shift]}'


class ChecklistSection(models.Model):
    """One table of a printed checklist."""

    class Form(models.TextChoices):
        EMAIL_WEB = 'email_web', 'Checklist Email, Web & Medsos'
        DEVICE = 'device', 'Checklist TOAST & Diseminasi'

    class Kind(models.TextChoices):
        EMAIL = 'email', 'Email: akses Y/N, dijawab (J/BJ), forward ke'
        WEB = 'web', 'Web: akses Y/N, dibaca (B/BB), disampaikan ke'
        CHECK = 'check', 'Checklist Ya/Tidak'

    form = models.CharField(max_length=20, choices=Form.choices)
    key = models.SlugField(max_length=40, unique=True)
    title = models.CharField(max_length=200)
    kind = models.CharField(max_length=10, choices=Kind.choices)
    order = models.PositiveSmallIntegerField(default=0)
    heading = models.CharField(max_length=200, blank=True,
                               help_text='Judul bagian dicetak di atas tabel, misalnya "A. CEK EMAIL (...)".')
    side_note = models.TextField(blank=True, help_text='Tabel email: dicetak di kolom samping, sepanjang semua baris.')
    note = models.TextField(blank=True, help_text='Dicetak di kiri bawah tabel, misalnya keterangan J/BJ.')
    note_right = models.TextField(blank=True, help_text='Dicetak di kanan bawah tabel, misalnya kontak admin.')

    class Meta:
        ordering = ['form', 'order', 'id']

    def __str__(self):
        return self.title


class ChecklistItem(models.Model):
    section = models.ForeignKey(ChecklistSection, on_delete=models.CASCADE, related_name='items')
    order = models.PositiveSmallIntegerField(default=0)
    name = models.CharField(max_length=300)
    address = models.CharField(max_length=300, blank=True, help_text='Alamat web, username email atau alamat aplikasi.')
    password = models.CharField(max_length=200, blank=True, help_text='Ikut dicetak di formulir.')
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ['section', 'order', 'id']

    def __str__(self):
        return self.name


# Values of the email/web answers.
ACCESS_CHOICES = (('Y', 'Y'), ('N', 'N'))
CONFIRM_CHOICES = {
    ChecklistSection.Kind.EMAIL: (('J', 'Dijawab'), ('BJ', 'Belum dijawab')),
    ChecklistSection.Kind.WEB: (('B', 'Dibaca'), ('BB', 'Belum dibaca')),
}


class ChecklistRecord(DutyRecord):
    """A filled-in checklist of a duty. Its code comes from the duty slot, so there is one per date and shift."""
    code_prefix = None
    form = None   # The ChecklistSection.Form of its catalog.
    title = None  # Title of the printed form.
    label = None  # Name of the job on the pages.

    check_time = models.TimeField(default=local_time_now)

    class Meta(DutyRecord.Meta):
        abstract = True

    def save(self, *args, **kwargs):
        setattr(self, self.code_field, duty_code(self.code_prefix, self.date, self.shift))
        super().save(*args, **kwargs)


class EmailWebRecord(ChecklistRecord):
    code_field = 'ew_id'
    code_prefix = 'EW'
    form = ChecklistSection.Form.EMAIL_WEB
    title = 'MONITORING EMAIL, WEB, MEDSOS DAN WRS-NG'
    label = 'Checklist Email, Web & Medsos'

    ew_id = models.CharField(max_length=20, unique=True, editable=False)


class DeviceRecord(ChecklistRecord):
    code_field = 'dc_id'
    code_prefix = 'DC'
    form = ChecklistSection.Form.DEVICE
    title = 'Checklist SeisComP (Backup), TOAST, Diseminasi, TSP dan WRS NG'
    label = 'Checklist TOAST & Diseminasi'

    dc_id = models.CharField(max_length=20, unique=True, editable=False)


class Answer(models.Model):
    """One checked item of a record, with a copy of the item as it was then (the item may change or go)."""
    item = models.ForeignKey(ChecklistItem, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    section_key = models.SlugField(max_length=40)
    section_title = models.CharField(max_length=200)
    kind = models.CharField(max_length=10, choices=ChecklistSection.Kind.choices)
    order = models.PositiveSmallIntegerField(default=0)
    item_name = models.CharField(max_length=300)
    item_address = models.CharField(max_length=300, blank=True)

    class Meta:
        abstract = True
        ordering = ['order', 'id']


class EmailWebAnswer(Answer):
    record = models.ForeignKey(EmailWebRecord, on_delete=models.CASCADE, related_name='answers')
    access = models.CharField(max_length=1, choices=ACCESS_CHOICES, blank=True)
    info = models.CharField(max_length=500, blank=True)  # Keterangan: the email/news seen, or what was done.
    confirmed = models.CharField(max_length=2, blank=True)  # J/BJ for email, B/BB for web (CONFIRM_CHOICES).
    forward_to = models.CharField(max_length=300, blank=True)


class DeviceAnswer(Answer):
    record = models.ForeignKey(DeviceRecord, on_delete=models.CASCADE, related_name='answers')
    ok = models.BooleanField(null=True)  # Ya / Tidak; None when not checked.
