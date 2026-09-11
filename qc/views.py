from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, TemplateView, UpdateView

from cl_seiscomp.models import StationListModel

from .forms import ErrorStationForm, QcRecordForm
from .models import ErrorStation, QcRecord


class QcRecordListView(TemplateView):
    template_name = 'qc/qcrecord_list.html'


class QcRecordCreateView(CreateView):
    model = QcRecord
    form_class = QcRecordForm
    template_name = 'qc/qcrecord_form.html'
    success_url = reverse_lazy('qc:qcrecord_list')


class QcRecordUpdateView(UpdateView):
    model = QcRecord
    form_class = QcRecordForm
    template_name = 'qc/qcrecord_form.html'
    success_url = reverse_lazy('qc:qcrecord_list')


class ErrorStationListView(ListView):
    model = ErrorStation
    template_name = 'qc/errorstation_list.html'
    context_object_name = 'errorstations'


class StationListContextMixin:
    """Gives the error station form the station list used to fill in the location."""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['station_list'] = list(StationListModel.objects.values('code', 'province', 'location', 'UPT'))
        return context


class ErrorStationCreateView(StationListContextMixin, CreateView):
    model = ErrorStation
    form_class = ErrorStationForm
    template_name = 'qc/errorstation_form.html'
    success_url = reverse_lazy('qc:errorstation_list')


class ErrorStationUpdateView(StationListContextMixin, UpdateView):
    model = ErrorStation
    form_class = ErrorStationForm
    template_name = 'qc/errorstation_form.html'
    success_url = reverse_lazy('qc:errorstation_list')


class ErrorStationDeleteView(DeleteView):
    model = ErrorStation
    template_name = 'qc/errorstation_confirm_delete.html'
    success_url = reverse_lazy('qc:errorstation_list')
