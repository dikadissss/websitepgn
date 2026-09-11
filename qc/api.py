from django.http import JsonResponse

from core import feeds
from core.api import RecordCsvView, RecordListAPIView, duty_fields, json_errors, parse_period

from .models import QcRecord


class QcRecordListAPIView(RecordListAPIView):
    model = QcRecord
    fields = {
        **duty_fields('qc_id'),
        'time': 'jam_pelaksanaan',
        'previous_group': 'kel_sebelum',
        'nip': 'NIP',
        'events_indonesia': 'event_indonesia',
        'events_abroad': 'event_luar',
        'previous_qc': 'qc_prev',
        'qc': 'qc',
    }
    search_fields = ('qc_id', 'operator__name', 'shift', 'NIP', 'qc_prev', 'qc')


class QcRecordCsvView(RecordCsvView):
    model = QcRecord
    filename = 'qc_records_export.csv'
    columns = (
        ('QC ID', 'qc_id'), ('Date', 'date'), ('Jam Pelaksanaan', 'jam_pelaksanaan'), ('Shift', 'shift'),
        ('Kelompok', 'kelompok'), ('Kel Sebelum', 'kel_sebelum'), ('Operator', 'operator__name'), ('NIP', 'NIP'),
        ('Event Indonesia', 'event_indonesia'), ('Event Luar', 'event_luar'), ('QC Sebelum', 'qc_prev'), ('QC', 'qc'),
    )


@json_errors
def events(request):
    """Events of the period for the QC form: CSV (stored in the record) and numbered rows (shown in the table)."""
    start, end = parse_period(request.GET)
    try:
        table = feeds.qc_events(start, end)
    except feeds.FeedError as error:
        return JsonResponse({'error': str(error)}, status=502)
    return JsonResponse({'csv': table.to_csv(index=False), 'rows': feeds.numbered(table).to_dict(orient='records')})
