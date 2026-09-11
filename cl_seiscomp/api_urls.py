from django.urls import path

from core.api import RecordExportView, RecordStatsAPIView

from . import api
from .models import CsRecordModel
from .reports import build_workbook

app_name = 'seiscomp_checklist'

urlpatterns = [
    path('records/', api.CsRecordListAPIView.as_view(), name='record_list'),
    path('records/stats/', RecordStatsAPIView.as_view(model=CsRecordModel), name='record_stats'),
    path('records/export.csv', api.CsRecordCsvView.as_view(), name='record_csv'),
    path('records/<int:pk>/export.xlsx',
         RecordExportView.as_view(model=CsRecordModel, build_workbook=build_workbook), name='record_xlsx'),
    path('records/<int:pk>/export.pdf',
         RecordExportView.as_view(model=CsRecordModel, build_workbook=build_workbook, file_format='pdf'), name='record_pdf'),
    path('station-status/', api.latest_station_status, name='station_status'),
]
