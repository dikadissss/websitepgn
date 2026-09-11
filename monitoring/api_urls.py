"""API of the two checklists, each under its own namespace (included in core/api_urls.py)."""
from django.urls import path

from core.api import RecordExportView, RecordStatsAPIView

from . import api
from .models import DeviceRecord, EmailWebRecord
from .reports import build_workbook


def record_patterns(model, list_view, csv_view):
    return [
        path('records/', list_view.as_view(), name='record_list'),
        path('records/stats/', RecordStatsAPIView.as_view(model=model), name='record_stats'),
        path('records/export.csv', csv_view.as_view(), name='record_csv'),
        path('records/<int:pk>/export.xlsx',
             RecordExportView.as_view(model=model, build_workbook=build_workbook), name='record_xlsx'),
        path('records/<int:pk>/export.pdf',
             RecordExportView.as_view(model=model, build_workbook=build_workbook, file_format='pdf'), name='record_pdf'),
    ]


email_web_patterns = record_patterns(EmailWebRecord, api.EmailWebListAPIView, api.EmailWebCsvView)
device_patterns = record_patterns(DeviceRecord, api.DeviceListAPIView, api.DeviceCsvView)
