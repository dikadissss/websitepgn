from django.http import JsonResponse

from core import feeds
from core.api import RecordCsvView, RecordListAPIView, duty_fields, json_errors, parse_period
from core.regions import count_indonesia

from .models import BastRecordModel
from .reports import parse_members


class BastRecordListAPIView(RecordListAPIView):
    model = BastRecordModel
    fields = {
        **duty_fields('bast_id'),
        'time': 'waktu_pelaksanaan',
        'next_group': 'kel_berikut',
        'supervisor_id': 'spv_id',
        'supervisor_name': 'spv__name',
        'nip': 'NIP',
        'events_indonesia': 'event_indonesia',
        'events_abroad': 'event_luar',
        'events_felt': 'event_dirasakan',
        'events_sent': 'event_dikirim',
        'events': 'events',
        'members': 'member',
        'gap_count': 'count_gaps',
        'spike_count': 'count_spikes',
        'blank_count': 'count_blanks',
        'checklist_time': 'waktu_cs',
        'poco_credit': 'pulsa_poco',
        'poco_expiry': 'poco_exp',
        'samsung_expiry': 'samsung_exp',
        'notes': 'notes',
    }
    search_fields = ('bast_id', 'operator__name', 'spv__name', 'shift', 'waktu_pelaksanaan', 'NIP', 'waktu_cs', 'notes')


class BastRecordCsvView(RecordCsvView):
    model = BastRecordModel
    filename = 'bast_records_export.csv'
    columns = (
        ('BAST ID', 'bast_id'), ('Date', 'date'), ('Waktu Pelaksanaan', 'waktu_pelaksanaan'), ('Shift', 'shift'),
        ('Kelompok', 'kelompok'), ('Kelompok Berikut', 'kel_berikut'), ('Events', 'events'),
        ('Petugas', 'operator__name'), ('Supervisor', 'spv__name'), ('NIP', 'NIP'),
        ('Event Indonesia', 'event_indonesia'), ('Event Luar', 'event_luar'), ('Event Dirasakan', 'event_dirasakan'),
        ('Event Dikirim', 'event_dikirim'), ('Members', 'member'), ('Count Gaps', 'count_gaps'),
        ('Count Spikes', 'count_spikes'), ('Count Blanks', 'count_blanks'), ('Waktu CS', 'waktu_cs'),
        ('Pulsa Poco', 'pulsa_poco'), ('POCO Expiry', 'poco_exp'), ('Samsung Expiry', 'samsung_exp'), ('Notes', 'notes'),
    )


def latest_record(request):
    """Values a new BAST carries over from the latest one: members' notes, phone credit and expiry dates."""
    record = BastRecordModel.objects.order_by('-date', '-id').first()
    if record is None:
        return JsonResponse({'error': 'No BAST records yet'}, status=404)
    return JsonResponse({
        'code': record.bast_id,
        'group': record.kelompok,
        'next_group': record.kel_berikut,
        'members': parse_members(record.member),
        'poco_credit': record.pulsa_poco,
        'poco_expiry': record.poco_exp,
        'samsung_expiry': record.samsung_exp,
    })


@json_errors
def events(request):
    """Events of the period in the BAST layout (numbered, with empty MMI/PGN/PGR columns to fill in), and how many
    lie inside the NTWC area (Event Indonesia) or outside it (Event Luar)."""
    start, end = parse_period(request.GET)
    try:
        table = feeds.bast_events(start, end)
    except feeds.FeedError as error:
        return JsonResponse({'error': str(error)}, status=502)
    indonesia, abroad = count_indonesia(table)
    return JsonResponse({
        'csv': table.to_csv(index=False),
        'rows': table.to_dict(orient='records'),
        'counts': {'indonesia': indonesia, 'abroad': abroad},
    })
