from django.urls import include, path

from monitoring.api_urls import device_patterns, email_web_patterns

from . import api

app_name = 'api'

urlpatterns = [
    path('operators/', api.OperatorListAPIView.as_view(), name='operator_list'),
    path('operators/<int:pk>/', api.OperatorDetailAPIView.as_view(), name='operator_detail'),
    path('groups/<int:number>/members/', api.GroupMembersAPIView.as_view(), name='group_members'),
    path('duty-summary/', api.DutySummaryAPIView.as_view(), name='duty_summary'),
    path('duty-summary/export.pdf', api.DutySummaryPdfView.as_view(), name='duty_summary_pdf'),
    path('bast/', include('bast.api_urls')),
    path('daily-report/', include('daily_report.api_urls')),
    path('qc/', include('qc.api_urls')),
    path('qcfm/', include('qcfm.api_urls')),
    path('seiscomp-checklist/', include('cl_seiscomp.api_urls')),
    path('tide-gauge/', include('tide_gauge.api_urls')),
    path('slmon/', include('slmon.api_urls')),
    path('email-web/', include((email_web_patterns, 'email_web'))),
    path('device-checklist/', include((device_patterns, 'device_checklist'))),
]
