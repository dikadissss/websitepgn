from django.urls import path

from core.api import RecordExportView, RecordStatsAPIView

from . import api
from .models import TideGaugeRecord
from .reports import build_workbook

app_name = 'tide_gauge'

urlpatterns = [
    path('records/', api.TideGaugeListAPIView.as_view(), name='record_list'),
    path('records/stats/', RecordStatsAPIView.as_view(model=TideGaugeRecord), name='record_stats'),
    path('records/export.csv', api.TideGaugeCsvView.as_view(), name='record_csv'),
    path('records/<int:pk>/export.xlsx',
         RecordExportView.as_view(model=TideGaugeRecord, build_workbook=build_workbook), name='record_xlsx'),
    path('records/<int:pk>/export.pdf',
         RecordExportView.as_view(model=TideGaugeRecord, build_workbook=build_workbook, file_format='pdf'),
         name='record_pdf'),
    path('fetch/', api.fetch, name='fetch'),
]
