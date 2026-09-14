import csv

from django.contrib import messages
from django.db.models import ProtectedError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import CreateView, ListView, TemplateView, UpdateView

from .choices import GROUP_CHOICES, SHIFT_CODES
from .duty import JOBS
from .forms import KelompokForm, OperatorForm
from .models import Kelompok, Operator


class HomeView(TemplateView):
    template_name = 'core/homepage.html'


class RecordDeleteView(View):
    """Delete a record on POST (list pages ask for confirmation first), then go back to ``success_url``."""
    model = None
    success_url = None  # URL name or path

    def post(self, request, pk):
        record = get_object_or_404(self.model, pk=pk)
        try:
            record.delete()
        except ProtectedError as error:
            messages.error(
                request,
                f'{record} tidak bisa dihapus karena masih tercatat di {len(error.protected_objects)} data pekerjaan.',
            )
        return redirect(self.success_url)


class OperatorListView(ListView):
    model = Operator
    template_name = 'core/operator_list.html'
    context_object_name = 'operator'


class OperatorCreateView(CreateView):
    model = Operator
    form_class = OperatorForm
    template_name = 'core/operator_form.html'
    success_url = reverse_lazy('core:operator_list')


class OperatorUpdateView(UpdateView):
    model = Operator
    form_class = OperatorForm
    template_name = 'core/operator_form.html'
    success_url = reverse_lazy('core:operator_list')


class OperatorBulkCreateView(View):
    template_name = 'core/operator_bulk_create.html'

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        csv_file = request.FILES.get('file')
        csv_data = request.POST.get('csv_data')

        if csv_file:
            if not csv_file.name.endswith('.csv'):
                return HttpResponse('File is not CSV type', status=400)
            csv_data = csv_file.read().decode('utf-8')
        elif not csv_data:
            return HttpResponse('No CSV file or data provided', status=400)

        Operator.objects.bulk_create(
            Operator(name=row[0], NIP=row[1]) for row in csv.reader(csv_data.splitlines()) if len(row) >= 2
        )
        return redirect('core:operator_list')


class KelompokListView(ListView):
    model = Kelompok
    template_name = 'core/kelompok_list.html'
    context_object_name = 'kelompok'


class KelompokCreateView(CreateView):
    model = Kelompok
    form_class = KelompokForm
    template_name = 'core/kelompok_form.html'
    success_url = reverse_lazy('core:kelompok_list')


class KelompokUpdateView(UpdateView):
    model = Kelompok
    form_class = KelompokForm
    template_name = 'core/kelompok_form.html'
    success_url = reverse_lazy('core:kelompok_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['existing_members'] = [str(operator.pk) for operator in self.object.ordered_members()]
        return context


class RekapView(TemplateView):
    """Recap of the jobs per job type, group and operator, and of every job of one duty slot."""
    template_name = 'core/rekap.html'

    def get_context_data(self, **kwargs):
        jobs = [{
            'key': job.key,
            'label': job.label,
            'list_url': reverse(f'api:{job.api_namespace}:record_list'),
            'stats_url': reverse(f'api:{job.api_namespace}:record_stats'),
            'csv_url': reverse(f'api:{job.api_namespace}:record_csv'),
            'xlsx_url': reverse(f'api:{job.api_namespace}:record_xlsx', args=[0]),
            'pdf_url': reverse(f'api:{job.api_namespace}:record_pdf', args=[0]),
            'edit_url': reverse(job.update_url_name, args=[0]),
        } for job in JOBS]
        return super().get_context_data(
            jobs=jobs,
            operators=Operator.objects.only('id', 'name'),
            groups=[number for number, _ in GROUP_CHOICES],
            shift_codes=[(code, shift.label) for code, (shift, _) in SHIFT_CODES.items()],
            **kwargs,
        )
