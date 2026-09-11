from django.urls import path

from core.api import RecordExportView, RecordStatsAPIView

from . import api
from .models import DailyReport
from .reports import build_pde_workbook, pde_filename

app_name = 'daily_report'

urlpatterns = [
    path('records/', api.DailyReportListAPIView.as_view(), name='record_list'),
    path('records/stats/', RecordStatsAPIView.as_view(model=DailyReport), name='record_stats'),
    path('records/export.csv', api.DailyReportCsvView.as_view(), name='record_csv'),
    # record_xlsx / record_pdf are the PDE, like the form exports of the other jobs.
    path('records/<int:pk>/pde.xlsx',
         RecordExportView.as_view(model=DailyReport, build_workbook=build_pde_workbook, filename=pde_filename),
         name='record_xlsx'),
    path('records/<int:pk>/pde.pdf',
         RecordExportView.as_view(model=DailyReport, build_workbook=build_pde_workbook, filename=pde_filename,
                                  file_format='pdf'),
         name='record_pdf'),
    path('records/<int:pk>/map.pdf', api.map_pdf, name='record_map_pdf'),
    path('records/<int:pk>/map/', api.redraw_map, name='record_map'),
    path('events/', api.day_events, name='events'),
    path('map-preview/', api.map_preview, name='map_preview'),
]
