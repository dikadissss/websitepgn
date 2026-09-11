from core.api import RecordCsvView, RecordListAPIView, duty_fields

from .models import DeviceRecord, EmailWebRecord


def list_view(model):
    return type(f'{model.__name__}ListAPIView', (RecordListAPIView,), {
        'model': model,
        'fields': {**duty_fields(model.code_field), 'check_time': 'check_time'},
        'search_fields': (model.code_field, 'operator__name', 'shift'),
    })


def csv_view(model, filename):
    return type(f'{model.__name__}CsvView', (RecordCsvView,), {
        'model': model,
        'filename': filename,
        'columns': (
            ('Kode', model.code_field), ('Tanggal', 'date'), ('Shift', 'shift'), ('Kelompok', 'kelompok'),
            ('Analis on Duty', 'operator__name'), ('Waktu Pengecekan', 'check_time'),
        ),
    })


EmailWebListAPIView = list_view(EmailWebRecord)
EmailWebCsvView = csv_view(EmailWebRecord, 'monitoring_email_web_export.csv')
DeviceListAPIView = list_view(DeviceRecord)
DeviceCsvView = csv_view(DeviceRecord, 'checklist_aplikasi_export.csv')
