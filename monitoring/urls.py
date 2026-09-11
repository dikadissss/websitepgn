from django.urls import path

from core.views import RecordDeleteView

from . import views

app_name = 'monitoring'


def job_patterns(job, prefix):
    return [
        path(f'{prefix}/', views.ChecklistListView.as_view(job=job), name=f'{job.name}_list'),
        path(f'{prefix}/create/', views.ChecklistCreateView.as_view(job=job, model=job.model),
             name=f'{job.name}_create'),
        path(f'{prefix}/update/<int:pk>/', views.ChecklistUpdateView.as_view(job=job, model=job.model),
             name=f'{job.name}_update'),
        path(f'{prefix}/delete-direct/<int:pk>/', RecordDeleteView.as_view(model=job.model, success_url=job.list_url),
             name=f'{job.name}_delete_direct'),
    ]


urlpatterns = [*job_patterns(views.EMAIL_WEB, 'email-web'), *job_patterns(views.DEVICE, 'device')]
