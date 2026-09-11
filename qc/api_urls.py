from django.urls import path

from core.api import RecordExportView, RecordStatsAPIView

from . import api
from .models import QcRecord
from .reports import build_workbook

app_name = 'qc'

urlpatterns = [
    path('records/', api.QcRecordListAPIView.as_view(), name='record_list'),
    path('records/stats/', RecordStatsAPIView.as_view(model=QcRecord), name='record_stats'),
    path('records/export.csv', api.QcRecordCsvView.as_view(), name='record_csv'),
    path('records/<int:pk>/export.xlsx',
         RecordExportView.as_view(model=QcRecord, build_workbook=build_workbook), name='record_xlsx'),
    path('records/<int:pk>/export.pdf',
         RecordExportView.as_view(model=QcRecord, build_workbook=build_workbook, file_format='pdf'), name='record_pdf'),
    path('events/', api.events, name='events'),
]
