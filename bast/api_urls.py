from django.urls import path

from core.api import RecordExportView, RecordStatsAPIView

from . import api
from .models import BastRecordModel
from .reports import build_workbook

app_name = 'bast'

urlpatterns = [
    path('records/', api.BastRecordListAPIView.as_view(), name='record_list'),
    path('records/latest/', api.latest_record, name='record_latest'),
    path('records/stats/', RecordStatsAPIView.as_view(model=BastRecordModel), name='record_stats'),
    path('records/export.csv', api.BastRecordCsvView.as_view(), name='record_csv'),
    path('records/<int:pk>/export.xlsx',
         RecordExportView.as_view(model=BastRecordModel, build_workbook=build_workbook), name='record_xlsx'),
    path('records/<int:pk>/export.pdf',
         RecordExportView.as_view(model=BastRecordModel, build_workbook=build_workbook, file_format='pdf'), name='record_pdf'),
    path('events/', api.events, name='events'),
]
