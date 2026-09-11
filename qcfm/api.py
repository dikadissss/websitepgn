from django.http import JsonResponse

from core import feeds
from core.api import RecordCsvView, RecordListAPIView, duty_fields, json_errors, parse_period

from .models import QcFmRecord


class QcFmRecordListAPIView(RecordListAPIView):
    model = QcFmRecord
    fields = {
        **duty_fields('qcfm_id'),
        'time': 'jam_pelaksanaan',
        'previous_group': 'kel_sebelum',
        'nip': 'NIP',
        'previous_qcfm': 'qcfm_prev',
        'qcfm': 'qcfm',
    }
    search_fields = ('qcfm_id', 'operator__name', 'shift', 'NIP', 'qcfm_prev', 'qcfm')


class QcFmRecordCsvView(RecordCsvView):
    model = QcFmRecord
    filename = 'qcfm_records_export.csv'
    columns = (
        ('QC ID', 'qcfm_id'), ('Date', 'date'), ('Jam Pelaksanaan', 'jam_pelaksanaan'), ('Shift', 'shift'),
        ('Kelompok', 'kelompok'), ('Kel Sebelum', 'kel_sebelum'), ('Operator', 'operator__name'), ('NIP', 'NIP'),
        ('QC Sebelum', 'qcfm_prev'), ('QC', 'qcfm'),
    )


@json_errors
def focal_mechanisms(request):
    """Focal mechanisms of the period for the QCFM form: CSV (stored in the record) and numbered rows."""
    start, end = parse_period(request.GET)
    try:
        table = feeds.focal_mechanisms(start, end)
    except feeds.FeedError as error:
        return JsonResponse({'error': str(error)}, status=502)
    return JsonResponse({'csv': table.to_csv(index=False), 'rows': feeds.numbered(table).to_dict(orient='records')})
