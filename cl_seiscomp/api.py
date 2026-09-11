from pathlib import Path

from django.core.files.storage import default_storage
from django.http import JsonResponse

from core.api import RecordCsvView, RecordListAPIView, duty_fields

from .models import CsRecordModel

# Written every few minutes by qc_download.py on the SeisComP host.
STATION_STATUS_PATH = Path(__file__).resolve().parent / 'static' / 'cl_seiscomp' / 'checklist.txt'


class CsRecordListAPIView(RecordListAPIView):
    model = CsRecordModel
    fields = {
        **duty_fields('cs_id'),
        'time': 'jam_pelaksanaan',
        'gaps': 'gaps',
        'spikes': 'spikes',
        'blanks': 'blanks',
        'slmon': 'slmon',
        'gap_count': 'count_gaps',
        'spike_count': 'count_spikes',
        'blank_count': 'count_blanks',
        'slmon_image': 'slmon_image',
    }
    search_fields = ('cs_id', 'operator__name', 'shift', 'jam_pelaksanaan', 'gaps', 'spikes', 'blanks')

    def serialize(self, row):
        if 'slmon_image' in row:
            row['slmon_image'] = default_storage.url(row['slmon_image']) if row['slmon_image'] else None
        return row


class CsRecordCsvView(RecordCsvView):
    model = CsRecordModel
    filename = 'cs_records_export.csv'
    columns = (
        ('CS ID', 'cs_id'), ('Date', 'date'), ('Shift', 'shift'), ('Jam Pelaksanaan', 'jam_pelaksanaan'),
        ('Kelompok', 'kelompok'), ('Operator', 'operator__name'), ('Gaps', 'gaps'), ('Spikes', 'spikes'),
        ('Blanks', 'blanks'), ('SLMON', 'slmon'), ('Count Gaps', 'count_gaps'), ('Count Spikes', 'count_spikes'),
        ('Count Blanks', 'count_blanks'), ('SLMON Image', 'slmon_image'),
    )


def latest_station_status(request):
    """Stations currently blank / with gaps / with spikes, from the checklist.txt sections
    ('Update <time>', 'Blank', 'Gaps', 'Spikes', separated by blank lines)."""
    try:
        text = STATION_STATUS_PATH.read_text()
    except FileNotFoundError:
        return JsonResponse({'error': 'Station status file not found'}, status=404)

    header, *blocks = text.split('\n\n')
    sections = {}
    for block in blocks:
        title, _, stations = block.partition('\n')
        sections[title.strip().lower()] = stations.strip('\n')
    return JsonResponse({
        'last_update': header.partition(' ')[2].strip(),
        'blanks': sections.get('blank', ''),
        'gaps': sections.get('gaps', ''),
        'spikes': sections.get('spikes', ''),
    })
