from django.urls import reverse_lazy
from django.views.generic import CreateView, TemplateView, UpdateView

from .forms import BastRecordForm
from .models import BastRecordModel


class BastRecordListView(TemplateView):
    template_name = 'bast/bastrecord_list.html'


class BastRecordCreateView(CreateView):
    model = BastRecordModel
    form_class = BastRecordForm
    template_name = 'bast/bastrecord_form.html'
    success_url = reverse_lazy('bast:bastrecord_list')


class BastRecordUpdateView(UpdateView):
    model = BastRecordModel
    form_class = BastRecordForm
    template_name = 'bast/bastrecord_form.html'
    success_url = reverse_lazy('bast:bastrecord_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['existing_data'] = self.object.events
        context['existing_member_data'] = self.object.member
        return context
