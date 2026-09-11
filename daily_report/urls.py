from django.urls import path

from core.views import RecordDeleteView

from . import views
from .models import DailyReport

app_name = 'daily_report'

urlpatterns = [
    path('', views.DailyReportListView.as_view(), name='dailyreport_list'),
    path('create/', views.DailyReportCreateView.as_view(), name='dailyreport_create'),
    path('update/<int:pk>/', views.DailyReportUpdateView.as_view(), name='dailyreport_update'),
    path('delete-direct/<int:pk>/',
         RecordDeleteView.as_view(model=DailyReport, success_url='daily_report:dailyreport_list'), name='dailyreport_delete_direct'),
]
