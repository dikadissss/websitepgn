from django.urls import path

from core.views import RecordDeleteView

from . import views
from .models import BastRecordModel

app_name = 'bast'

urlpatterns = [
    path('', views.BastRecordListView.as_view(), name='bastrecord_list'),
    path('create/', views.BastRecordCreateView.as_view(), name='bastrecord_create'),
    path('update/<int:pk>/', views.BastRecordUpdateView.as_view(), name='bastrecord_update'),
    path('delete-direct/<int:pk>/',
         RecordDeleteView.as_view(model=BastRecordModel, success_url='bast:bastrecord_list'), name='bastrecord_delete_direct'),
]
