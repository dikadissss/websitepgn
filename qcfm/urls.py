from django.urls import path

from core.views import RecordDeleteView

from . import views
from .models import QcFmRecord

app_name = 'qcfm'

urlpatterns = [
    path('', views.QcFmRecordListView.as_view(), name='qcfmrecord_list'),
    path('create/', views.QcFmRecordCreateView.as_view(), name='qcfmrecord_create'),
    path('update/<int:pk>/', views.QcFmRecordUpdateView.as_view(), name='qcfmrecord_update'),
    path('delete-direct/<int:pk>/',
         RecordDeleteView.as_view(model=QcFmRecord, success_url='qcfm:qcfmrecord_list'), name='qcfmrecord_delete_direct'),
]
