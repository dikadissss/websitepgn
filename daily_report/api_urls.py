from django.urls import path

from core.api import RecordExportView, RecordStatsAPIView

from . import api
from .models import DailyReport
from .reports import build_report_workbook, report_filename

app_name = 'daily_report'

urlpatterns = [
    path('records/', api.DailyReportListAPIView.as_view(), name='record_list'),
    path('records/stats/', RecordStatsAPIView.as_view(model=DailyReport), name='record_stats'),
    path('records/export.csv', api.DailyReportCsvView.as_view(), name='record_csv'),
    # record_xlsx / record_pdf (the Rekap exports) hold the whole report: the Peta Harian page, then the PDE.
    path('records/<int:pk>/report.xlsx',
         RecordExportView.as_view(model=DailyReport, build_workbook=build_report_workbook, filename=report_filename),
         name='record_xlsx'),
    path('records/<int:pk>/report.pdf', api.report_pdf, name='record_pdf'),
    path('records/<int:pk>/map.pdf', api.map_pdf, name='record_map_pdf'),
    path('records/<int:pk>/map/', api.redraw_map, name='record_map'),
    path('events/', api.day_events, name='events'),
    path('map-preview/', api.map_preview, name='map_preview'),
]
