from pathlib import Path

from django.conf import settings
from django.db import models
from django.utils import timezone

from .feed import BLANK, STATION_COLORS

MAP_DIRECTORY = 'slmon'


def media_path(name):
    return Path(settings.MEDIA_ROOT) / name


def media_src(name):
    """URL of a media file with its modification time, so browsers reload a redrawn map."""
    url = f"/{settings.MEDIA_URL.strip('/')}/{name}"
    path = media_path(name)
    return f'{url}?v={int(path.stat().st_mtime)}' if path.exists() else url


class SlmonSnapshot(models.Model):
    """Status of every station at one time of the slmon JSON.

    Its two maps (the Peta and the slmon2 view, see slmon.maps) are PNG files under MEDIA_ROOT, not stored in the
    database. A checklist that uses a snapshot keeps its own copy of a map (CsRecordModel.slmon_image), so
    snapshots can be redrawn or deleted freely."""
    data_time = models.DateTimeField(unique=True)  # The "time" of the JSON records (UTC).
    fetched_at = models.DateTimeField(auto_now_add=True)
    stations = models.JSONField(default=list)  # [network, code, longitude, latitude, color1, status] per station.

    class Meta:
        ordering = ['-data_time']

    def __str__(self):
        return f'SLMON {self.local_time:%Y-%m-%d %H:%M:%S} WIB'

    def delete(self, *args, **kwargs):
        result = super().delete(*args, **kwargs)
        self.map_path.unlink(missing_ok=True)
        self.monitor_map_path.unlink(missing_ok=True)
        return result

    @property
    def local_time(self):
        return timezone.localtime(self.data_time)

    @property
    def status_counts(self):
        """Number of stations of each status, in STATION_COLORS order."""
        counts = dict.fromkeys(STATION_COLORS, 0)
        for *_, status in self.stations:
            counts[status] = counts.get(status, 0) + 1
        return counts

    @property
    def total(self):
        return len(self.stations)

    @property
    def blank(self):
        return sum(1 for *_, status in self.stations if status == BLANK)

    @property
    def not_blank(self):
        return self.total - self.blank

    def percentage(self, count):
        return f'{count / self.total * 100:.1f}' if self.total else '0.0'

    @property
    def caption(self):
        """Caption posted under the map (the lines of the old slmon_gui2.py tool, with the colons aligned)."""
        return (
            f'Monitoring kondisi sinyal SeisComP ({self.local_time:%Y-%m-%d %H:%M:%S} WIB)\n'
            'Dalam Negeri : \n'
            f"   {'Jumlah Sensor':<24}: {self.total}\n"
            f"       {':: Not Blank':<20}: {self.not_blank} ({self.percentage(self.not_blank)} %)\n"
            f"       {':: Blank':<20}: {self.blank} ({self.percentage(self.blank)} %)"
        )

    @property
    def label(self):
        return f'{self.local_time:%Y-%m-%d %H:%M} WIB · Blank {self.blank}/{self.total}'

    # The Peta (gempa.de tiles, graticule).

    @property
    def map_name(self):
        return f'{MAP_DIRECTORY}/slmon_{self.data_time:%Y%m%d_%H%M%S}.png'

    @property
    def map_path(self):
        return media_path(self.map_name)

    @property
    def map_src(self):
        return media_src(self.map_name)

    # The slmon2 view (OpenStreetMap tiles, summary box and pie chart).

    @property
    def monitor_map_name(self):
        return f'{MAP_DIRECTORY}/slmon2_{self.data_time:%Y%m%d_%H%M%S}.png'

    @property
    def monitor_map_path(self):
        return media_path(self.monitor_map_name)

    @property
    def monitor_map_src(self):
        return media_src(self.monitor_map_name)

    def as_json(self):
        return {
            'id': self.pk,
            'label': self.label,
            'data_time': self.local_time.isoformat(),
            'map_url': self.map_src,
            'monitor_map_url': self.monitor_map_src,
            'caption': self.caption,
            'total': self.total,
            'blank': self.blank,
            'not_blank': self.not_blank,
        }
