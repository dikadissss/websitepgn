"""API of the Checklist Tide Gauge, under /api/v1/tide-gauge/."""
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from core.api import RecordCsvView, RecordListAPIView, duty_fields

from . import feed
from .models import TideGaugeRecord

COUNT_FIELDS = {'total': 'count_total', 'gaps': 'count_gaps', 'spike': 'count_spike', 'blank': 'count_blank'}


class TideGaugeListAPIView(RecordListAPIView):
    model = TideGaugeRecord
    fields = {**duty_fields('tg_id'), 'check_time': 'check_time', **COUNT_FIELDS}
    search_fields = ('tg_id', 'operator__name', 'shift')


class TideGaugeCsvView(RecordCsvView):
    model = TideGaugeRecord
    filename = 'checklist_tide_gauge_export.csv'
    columns = (
        ('Kode', 'tg_id'), ('Tanggal', 'date'), ('Shift', 'shift'), ('Kelompok', 'kelompok'),
        ('Operator on Duty', 'operator__name'), ('Waktu Pengecekan', 'check_time'),
        ('Web Bisa Diakses', 'web_accessible'), ('Total Alat', 'count_total'), ('Gaps', 'count_gaps'),
        ('Spike', 'count_spike'), ('Blank', 'count_blank'),
    )


@require_POST
def fetch(request):
    """Read the monitor's latencies now ("Ambil data Tide Gauge"); nothing is stored until the form is saved."""
    try:
        data_time, stations = feed.parse_stations(feed.fetch_latencies())
    except feed.TideGaugeError as error:
        return JsonResponse({'error': str(error)}, status=502)
    return JsonResponse({'data_time': data_time, 'stations': stations, 'summary': feed.summary(stations)})
