from dataclasses import dataclass

from django.db import transaction
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import CreateView, TemplateView, UpdateView

from .answers import group_sections, rows_for, save_answers
from .forms import checklist_form
from .models import DeviceRecord, EmailWebRecord


@dataclass(frozen=True)
class ChecklistJob:
    name: str           # Prefix of the page URL names: '<name>_list', '<name>_create', ...
    model: type
    api_namespace: str  # Under 'api:' (core/api_urls.py).

    @property
    def title(self):
        return self.model.title

    @property
    def list_url(self):
        return f'monitoring:{self.name}_list'

    @property
    def create_url(self):
        return f'monitoring:{self.name}_create'

    @property
    def update_url(self):
        return f'monitoring:{self.name}_update'

    @property
    def delete_url(self):
        return f'monitoring:{self.name}_delete_direct'

    @property
    def api_list_url(self):
        return f'api:{self.api_namespace}:record_list'


EMAIL_WEB = ChecklistJob('email_web', EmailWebRecord, 'email_web')
DEVICE = ChecklistJob('device', DeviceRecord, 'device_checklist')


class ChecklistListView(TemplateView):
    template_name = 'monitoring/record_list.html'
    job = None

    def get_context_data(self, **kwargs):
        return super().get_context_data(job=self.job, **kwargs)


class ChecklistFormMixin:
    template_name = 'monitoring/record_form.html'
    job = None

    def get_form_class(self):
        return checklist_form(self.job.model)

    def get_success_url(self):
        return reverse(self.job.list_url)

    def rows(self):
        return rows_for(self.object, self.job.model)

    def get_context_data(self, **kwargs):
        return super().get_context_data(job=self.job, sections=group_sections(self.rows()), **kwargs)

    def form_valid(self, form):
        rows = self.rows()  # Before saving: the catalog for a new record, its answers otherwise.
        with transaction.atomic():
            self.object = form.save()
            save_answers(self.object, rows, self.request.POST)
        return redirect(self.get_success_url())


class ChecklistCreateView(ChecklistFormMixin, CreateView):
    pass


class ChecklistUpdateView(ChecklistFormMixin, UpdateView):
    pass
