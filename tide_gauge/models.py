"""Checklist Tide Gauge: the signal of the sea level stations of the InaTNT monitor, checked once per duty."""
from django.db import models

from core.choices import local_time_now
from core.models import DutyRecord
from monitoring.models import duty_code

from . import feed


class TideGaugeRecord(DutyRecord):
    """The stations as fetched from the monitor (feed.parse_stations), with the status confirmed by the officer.
    Its code comes from the duty slot, so there is one per date and shift."""
    code_field = 'tg_id'
    code_prefix = 'TG'
    title = 'MONITORING SINYAL TSUNAMI GAUGES, TIDEGAUGES, BUOYS, AWS, DAN CBT'  # Title of the printed form.
    label = 'Checklist Tide Gauge'  # Name of the job on the pages.

    tg_id = models.CharField(max_length=20, unique=True, editable=False)
    check_time = models.TimeField(default=local_time_now)
    data_time = models.DateTimeField(null=True, blank=True)  # Time of the monitor's data.
    web_accessible = models.BooleanField(default=True)  # "Web Tide Gauge bisa di Akses" of the printed form.
    stations = models.JSONField(default=list, blank=True)
    # Counted from the stations on save, for the list and the CSV.
    count_total = models.PositiveSmallIntegerField(default=0)
    count_gaps = models.PositiveSmallIntegerField(default=0)
    count_spike = models.PositiveSmallIntegerField(default=0)
    count_blank = models.PositiveSmallIntegerField(default=0)

    class Meta(DutyRecord.Meta):
        # DutyRecord's '%(app_label)s_%(class)s_slot' would be longer than the 30 characters Django allows.
        indexes = [models.Index(fields=['date', 'shift', 'kelompok'], name='tide_gauge_record_slot')]

    def save(self, *args, **kwargs):
        self.tg_id = duty_code(self.code_prefix, self.date, self.shift)
        counts = feed.count_statuses(self.stations)
        self.count_total, self.count_gaps, self.count_spike, self.count_blank = (
            counts['total'], counts['gaps'], counts['spike'], counts['blank'])
        super().save(*args, **kwargs)

    def summary(self):
        return feed.summary(self.stations)
