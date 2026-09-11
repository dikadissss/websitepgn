from django.urls import path

from . import views
from .models import Kelompok, Operator

app_name = 'core'

urlpatterns = [
    path('', views.HomeView.as_view(), name='core'),
    path('operator/', views.OperatorListView.as_view(), name='operator_list'),
    path('operator/create/', views.OperatorCreateView.as_view(), name='operator_create'),
    path('operator/update/<int:pk>/', views.OperatorUpdateView.as_view(), name='operator_update'),
    path('operator/delete-direct/<int:pk>/',
         views.RecordDeleteView.as_view(model=Operator, success_url='core:operator_list'), name='operator_delete_direct'),
    path('operator/bulk-create/', views.OperatorBulkCreateView.as_view(), name='operator_bulk_create'),
    path('kelompok/', views.KelompokListView.as_view(), name='kelompok_list'),
    path('kelompok/create/', views.KelompokCreateView.as_view(), name='kelompok_create'),
    path('kelompok/update/<int:pk>/', views.KelompokUpdateView.as_view(), name='kelompok_update'),
    path('kelompok/delete-direct/<int:pk>/',
         views.RecordDeleteView.as_view(model=Kelompok, success_url='core:kelompok_list'), name='kelompok_delete_direct'),
]
