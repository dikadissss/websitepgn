from django.db import models
from PIL import Image

from core.models import DutyRecord

WAKTU = (
    ('00:00 WIB', '00:00 WIB'),
    ('06:00 WIB', '06:00 WIB'),
    ('12:00 WIB', '12:00 WIB'),
    ('18:00 WIB', '18:00 WIB'),
)

SLMON_IMAGE_MAX_SIZE = (1800, 1000)  # Width, height: keeps the SLMON maps (1728 x 832) sharp in the PDF.


def keep_known_stations(text, station_codes):
    """Uppercase a newline-separated station list and drop codes that are not in the station list."""
    stations = [line.strip() for line in (text or '').upper().splitlines()]
    stations = [code for code in stations if code in station_codes]
    return '\n'.join(stations), len(stations)


class CsRecordModel(DutyRecord):
    code_field = 'cs_id'

    cs_id = models.CharField(max_length=16, default='0', unique=True)
    jam_pelaksanaan = models.CharField(max_length=20, choices=WAKTU, default='12:00 WIB')
    gaps = models.TextField(max_length=10000, null=True, blank=True)
    spikes = models.TextField(max_length=10000, null=True, blank=True)
    blanks = models.TextField(max_length=10000, null=True, blank=True)
    slmon = models.PositiveIntegerField(null=True, blank=True, default=0)
    count_gaps = models.PositiveIntegerField(null=True, blank=True, default=0)
    count_spikes = models.PositiveIntegerField(null=True, blank=True, default=0)
    count_blanks = models.PositiveIntegerField(null=True, blank=True, default=0)
    slmon_image = models.ImageField(upload_to='cl_seiscomp/slmon_images/', null=True, blank=True)

    def save(self, *args, **kwargs):
        station_codes = set(StationListModel.objects.values_list('code', flat=True))
        self.gaps, self.count_gaps = keep_known_stations(self.gaps, station_codes)
        self.spikes, self.count_spikes = keep_known_stations(self.spikes, station_codes)
        self.blanks, self.count_blanks = keep_known_stations(self.blanks, station_codes)

        super().save(*args, **kwargs)

        if self.slmon_image:
            with Image.open(self.slmon_image.path) as img:
                if img.width > SLMON_IMAGE_MAX_SIZE[0] or img.height > SLMON_IMAGE_MAX_SIZE[1]:
                    img.thumbnail(SLMON_IMAGE_MAX_SIZE)
                    img.save(self.slmon_image.path)


class StationListModel(models.Model):
    network = models.CharField(max_length=5)
    code = models.CharField(max_length=10)
    province = models.CharField(max_length=50)
    location = models.CharField(max_length=200)
    digitizer_type = models.CharField(max_length=100)
    UPT = models.CharField(max_length=50)
    longitude = models.FloatField(null=True, blank=True)
    latitude = models.FloatField(null=True, blank=True)

    def __str__(self):
        return self.code
