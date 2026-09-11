from django.urls import path

from core.views import RecordDeleteView

from . import views
from .models import TideGaugeRecord

app_name = 'tide_gauge'

urlpatterns = [
    path('', views.RecordListView.as_view(), name='record_list'),
    path('create/', views.RecordCreateView.as_view(), name='record_create'),
    path('update/<int:pk>/', views.RecordUpdateView.as_view(), name='record_update'),
    path('delete-direct/<int:pk>/',
         RecordDeleteView.as_view(model=TideGaugeRecord, success_url='tide_gauge:record_list'),
         name='record_delete_direct'),
]
