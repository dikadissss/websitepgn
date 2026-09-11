from django.urls import reverse_lazy
from django.views.generic import CreateView, TemplateView, UpdateView

from .forms import QcFmRecordForm
from .models import QcFmRecord


class QcFmRecordListView(TemplateView):
    template_name = 'qcfm/qcfmrecord_list.html'


class QcFmRecordCreateView(CreateView):
    model = QcFmRecord
    form_class = QcFmRecordForm
    template_name = 'qcfm/qcfmrecord_form.html'
    success_url = reverse_lazy('qcfm:qcfmrecord_list')


class QcFmRecordUpdateView(UpdateView):
    model = QcFmRecord
    form_class = QcFmRecordForm
    template_name = 'qcfm/qcfmrecord_form.html'
    success_url = reverse_lazy('qcfm:qcfmrecord_list')
