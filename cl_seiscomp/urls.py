from django.urls import path

from core.views import RecordDeleteView

from . import views
from .models import CsRecordModel

app_name = 'cl_seiscomp'

urlpatterns = [
    path('', views.CsListView.as_view(), name='cs_list'),
    path('station_list/', views.StationListView.as_view(), name='station_list'),
    path('station/create/', views.StationCreateView.as_view(), name='sl_create'),
    path('station/update/<int:pk>/', views.StationUpdateView.as_view(), name='sl_update'),
    path('station/delete/<int:pk>/', views.StationDeleteView.as_view(), name='sl_delete'),
    path('station/bulk_create/', views.StationBulkCreateView.as_view(), name='sl_bulk_create'),
    path('cs/create/', views.CsCreateView.as_view(), name='cs_create'),
    path('cs/update/<int:pk>/', views.CsUpdateView.as_view(), name='cs_update'),
    path('cs/delete/<int:pk>/', RecordDeleteView.as_view(model=CsRecordModel, success_url='cl_seiscomp:cs_list'), name='cs_delete'),
    path('stats/', views.StatsView.as_view(), name='stats'),
]
