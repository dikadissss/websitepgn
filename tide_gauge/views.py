from django.urls import reverse_lazy
from django.views.generic import CreateView, TemplateView, UpdateView

from . import feed
from .forms import TideGaugeRecordForm
from .models import TideGaugeRecord


class RecordListView(TemplateView):
    template_name = 'tide_gauge/record_list.html'
    extra_context = {'title': TideGaugeRecord.label}


class RecordFormMixin:
    model = TideGaugeRecord
    form_class = TideGaugeRecordForm
    template_name = 'tide_gauge/record_form.html'
    success_url = reverse_lazy('tide_gauge:record_list')

    def get_context_data(self, **kwargs):
        return super().get_context_data(title=TideGaugeRecord.label, categories=feed.categories(),
                                        tg_host=feed.TG_HOST, **kwargs)


class RecordCreateView(RecordFormMixin, CreateView):
    pass


class RecordUpdateView(RecordFormMixin, UpdateView):
    pass
