from django.urls import path

from core.views import RecordDeleteView

from . import views
from .models import QcRecord

app_name = 'qc'

urlpatterns = [
    path('', views.QcRecordListView.as_view(), name='qcrecord_list'),
    path('create/', views.QcRecordCreateView.as_view(), name='qcrecord_create'),
    path('update/<int:pk>/', views.QcRecordUpdateView.as_view(), name='qcrecord_update'),
    path('delete-direct/<int:pk>/',
         RecordDeleteView.as_view(model=QcRecord, success_url='qc:qcrecord_list'), name='qcrecord_delete_direct'),
    path('errorstations/', views.ErrorStationListView.as_view(), name='errorstation_list'),
    path('errorstations/add/', views.ErrorStationCreateView.as_view(), name='errorstation_add'),
    path('errorstations/<int:pk>/edit/', views.ErrorStationUpdateView.as_view(), name='errorstation_edit'),
    path('errorstations/<int:pk>/delete/', views.ErrorStationDeleteView.as_view(), name='errorstation_delete'),
]
