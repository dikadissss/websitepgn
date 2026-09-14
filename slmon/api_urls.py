from django.urls import path

from . import api

app_name = 'slmon'

urlpatterns = [
    path('preview/', api.preview, name='preview'),
    path('snapshots/', api.snapshots, name='snapshots'),
]
