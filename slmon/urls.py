from django.urls import path

from . import views

app_name = 'slmon'

urlpatterns = [
    path('', views.SlmonView.as_view(), name='index'),
    path('fetch/', views.fetch, name='fetch'),
    path('<int:pk>/', views.SlmonView.as_view(), name='detail'),
]
