from django.urls import path

from . import api

app_name = 'slmon'

urlpatterns = [
    path('fetch/', api.fetch, name='fetch'),
    path('snapshots/', api.snapshots, name='snapshots'),
]
