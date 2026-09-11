from django.urls import path

from core.api import RecordExportView, RecordStatsAPIView

from . import api
from .models import QcFmRecord
from .reports import build_workbook

app_name = 'qcfm'

urlpatterns = [
    path('records/', api.QcFmRecordListAPIView.as_view(), name='record_list'),
    path('records/stats/', RecordStatsAPIView.as_view(model=QcFmRecord), name='record_stats'),
    path('records/export.csv', api.QcFmRecordCsvView.as_view(), name='record_csv'),
    path('records/<int:pk>/export.xlsx',
         RecordExportView.as_view(model=QcFmRecord, build_workbook=build_workbook), name='record_xlsx'),
    path('records/<int:pk>/export.pdf',
         RecordExportView.as_view(model=QcFmRecord, build_workbook=build_workbook, file_format='pdf'), name='record_pdf'),
    path('focal-mechanisms/', api.focal_mechanisms, name='focal_mechanisms'),
]
