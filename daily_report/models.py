import datetime
from pathlib import Path

from django.conf import settings
from django.db import models

from core.choices import Shift
from core.models import DutyRecord, Operator

from .data import events_table

MAP_DIRECTORY = 'daily_report'


class DailyReport(DutyRecord):
    """PDE and epicenter map of one UTC day.

    The report of day D belongs to the Pagi duty of D+1 (the UTC day ends at 07:00 WIB), so ``save()`` derives
    the duty date and shift from ``report_date``. The events are kept here because index3.txt only lists the
    last few days; the map image is a file under MEDIA_ROOT, not stored in the database.
    """
    code_field = 'report_id'

    report_id = models.CharField(max_length=16, unique=True, editable=False)
    report_date = models.DateField(unique=True)
    # No longer asked: "Mengetahui" is signed by hand on the printed report. Kept for old records.
    spv = models.ForeignKey(Operator, on_delete=models.PROTECT, related_name='supervised_daily_reports',
                            null=True, blank=True)
    events = models.TextField(blank=True, default='')  # CSV with the core.feeds.DAILY_EVENT_COLUMNS columns.

    def save(self, *args, **kwargs):
        self.report_id = f'DR-{self.report_date:%Y-%m-%d}'
        self.date = self.report_date + datetime.timedelta(days=1)
        self.shift = Shift.PAGI
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        result = super().delete(*args, **kwargs)
        self.map_path.unlink(missing_ok=True)
        return result

    def event_table(self):
        return events_table(self.events)

    @property
    def map_name(self):
        return f'{MAP_DIRECTORY}/peta_{self.report_date:%Y-%m-%d}.png'

    @property
    def map_path(self):
        return Path(settings.MEDIA_ROOT) / self.map_name

    @property
    def map_url(self):
        return f"/{settings.MEDIA_URL.strip('/')}/{self.map_name}"
