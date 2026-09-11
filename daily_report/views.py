from django.contrib import messages
from django.urls import reverse
from django.views.generic import CreateView, TemplateView, UpdateView

from .data import json_records
from .forms import DailyReportForm
from .maps import render_map
from .models import DailyReport


class DailyReportListView(TemplateView):
    template_name = 'daily_report/dailyreport_list.html'


def draw_map(request, report):
    """(Re)draw the report's map file, telling the officer when tiles could not be downloaded."""
    try:
        missing = render_map(report.event_table(), report.map_path)
    except OSError as error:
        messages.warning(request, f'Peta belum bisa dibuat ({error}). Coba lagi dengan tombol "Plot ulang peta".')
        return
    if missing:
        messages.warning(request, f'{missing} potongan peta tidak bisa diunduh dari tiles.gempa.de. '
                                  'Coba lagi dengan tombol "Plot ulang peta".')


class DailyReportFormMixin:
    model = DailyReport
    form_class = DailyReportForm
    template_name = 'daily_report/dailyreport_form.html'

    def form_valid(self, form):
        response = super().form_valid(form)
        draw_map(self.request, self.object)
        return response

    def get_success_url(self):
        return reverse('daily_report:dailyreport_update', args=[self.object.pk])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        report = self.object
        context['event_rows'] = []  # Rendered into the PDE table by the page's script.
        if report is not None:
            context['event_rows'] = json_records(report.event_table())
            if report.map_path.exists():
                context['map_src'] = f'{report.map_url}?v={int(report.map_path.stat().st_mtime)}'
        return context


class DailyReportCreateView(DailyReportFormMixin, CreateView):
    pass


class DailyReportUpdateView(DailyReportFormMixin, UpdateView):
    pass
