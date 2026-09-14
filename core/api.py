"""JSON API under /api/v1/ shared by the duty record apps.

Record lists speak Tabulator's remote mode: ``page``/``size``, ``sort[i][field|dir]`` and
``filter[i][field|type|value]``, where the filter field ``search`` looks in every searchable column.
Lists, stats and CSV exports also take the duty filters ``group``, ``operator``, ``shift``
(P, S, M1, M2 or a shift name), ``date``, ``date_from``, ``date_to`` and ``code``.
"""
import datetime
import functools
import math
import re
import subprocess

from django.db.models import Count, F, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views import View

from .choices import SHIFT_CODES, resolve_duty_slot
from .dates import convert_to_roman
from .duty import JOBS
from .exports import (PdfConversionError, csv_response, documents_to_pdf, export_filename, pdf_file_response,
                      pdf_response, xlsx_response)
from .models import Kelompok, Operator

DEFAULT_PAGE_SIZE = 25
MAX_PAGE_SIZE = 100
MAX_EXPORT_RECORDS = 100  # Forms in one Per Pekerjaan PDF export: each one goes through LibreOffice.
FILTER_LOOKUPS = {
    'like': 'icontains', '=': 'exact', '!=': 'exact', '<': 'lt', '<=': 'lte', '>': 'gt', '>=': 'gte',
    'starts': 'istartswith', 'ends': 'iendswith',
}


class BadRequest(Exception):
    pass


def json_errors(view):
    """Answer BadRequest raised by the view with a 400 JSON error."""
    @functools.wraps(view)
    def wrapper(request, *args, **kwargs):
        try:
            return view(request, *args, **kwargs)
        except BadRequest as error:
            return JsonResponse({'error': str(error)}, status=400)
    return wrapper


class ApiView(View):
    def dispatch(self, request, *args, **kwargs):
        return json_errors(super().dispatch)(request, *args, **kwargs)


def parse_int(value, name):
    try:
        return int(value)
    except (TypeError, ValueError):
        raise BadRequest(f"'{name}' must be an integer") from None


def parse_date(value, name):
    try:
        return datetime.date.fromisoformat(value)
    except (TypeError, ValueError):
        raise BadRequest(f"'{name}' must be a date (YYYY-MM-DD)") from None


def parse_period(params):
    """The 'start' and 'end' datetimes ('YYYY-MM-DD HH:MM:SS') of a bulletin request."""
    try:
        return datetime.datetime.fromisoformat(params['start']), datetime.datetime.fromisoformat(params['end'])
    except (KeyError, ValueError):
        raise BadRequest("'start' and 'end' must be datetimes (YYYY-MM-DD HH:MM:SS)") from None


def duty_fields(code_field):
    """API keys -> ORM lookups for the fields every duty record has."""
    return {
        'id': 'id',
        'code': code_field,
        'date': 'date',
        'shift': 'shift',
        'group': 'kelompok',
        'operator_id': 'operator_id',
        'operator_name': 'operator__name',
    }


def filter_duty_records(queryset, params):
    if params.get('code'):
        queryset = queryset.filter(**{queryset.model.code_field: params['code']})
    if params.get('group'):
        queryset = queryset.filter(kelompok=parse_int(params['group'], 'group'))
    if params.get('operator'):
        queryset = queryset.filter(operator_id=parse_int(params['operator'], 'operator'))
    shift = params.get('shift')
    if params.get('date'):
        date = parse_date(params['date'], 'date')
        if shift in SHIFT_CODES:
            date, shift = resolve_duty_slot(date, shift)
        queryset = queryset.filter(date=date)
    if shift:
        queryset = queryset.filter(shift=SHIFT_CODES[shift][0] if shift in SHIFT_CODES else shift)
    if params.get('date_from'):
        queryset = queryset.filter(date__gte=parse_date(params['date_from'], 'date_from'))
    if params.get('date_to'):
        queryset = queryset.filter(date__lte=parse_date(params['date_to'], 'date_to'))
    return queryset


def indexed_params(params, name):
    """Tabulator sends lists of objects as name[0][field]=...; rebuild them as a list of dicts."""
    items = {}
    for key, value in params.items():
        match = re.fullmatch(rf'{name}\[(\d+)\]\[(\w+)\]', key)
        if match:
            items.setdefault(int(match[1]), {})[match[2]] = value
    return [items[index] for index in sorted(items)]


class RecordListAPIView(ApiView):
    """Records of one duty model, as a Tabulator page ({last_page, last_row, data}) when ``page`` is given,
    otherwise as a plain list of at most ``limit`` (default and maximum 100) records."""
    model = None
    fields = {}          # API key -> ORM lookup
    search_fields = ()   # ORM lookups searched by the 'search' filter

    def get(self, request):
        params = request.GET
        records = filter_duty_records(self.model.objects.all(), params)
        records = self.sort(self.filter(records, params), params)

        if 'page' not in params:
            limit = min(parse_int(params.get('limit', MAX_PAGE_SIZE), 'limit'), MAX_PAGE_SIZE)
            return JsonResponse([self.serialize(row) for row in self.rows(records)[:limit]], safe=False)

        size = min(max(parse_int(params.get('size', DEFAULT_PAGE_SIZE), 'size'), 1), MAX_PAGE_SIZE)
        page = max(parse_int(params['page'], 'page'), 1)
        total = records.count()
        rows = self.rows(records)[(page - 1) * size:page * size]
        return JsonResponse({
            'last_page': max(math.ceil(total / size), 1),
            'last_row': total,
            'data': [self.serialize(row) for row in rows],
        })

    def rows(self, records):
        same_name = [key for key, lookup in self.fields.items() if key == lookup]
        renamed = {key: F(lookup) for key, lookup in self.fields.items() if key != lookup}
        return records.values(*same_name, **renamed)

    def serialize(self, row):
        return row

    def filter(self, records, params):
        for item in indexed_params(params, 'filter'):
            field, kind, value = item.get('field'), item.get('type', 'like'), item.get('value', '')
            if field == 'search':
                if value:
                    records = records.filter(functools.reduce(
                        Q.__or__, (Q(**{f'{lookup}__icontains': value}) for lookup in self.search_fields), Q()))
                continue
            if field not in self.fields or kind not in FILTER_LOOKUPS:
                raise BadRequest(f"Cannot filter '{field}' with '{kind}'")
            condition = Q(**{f'{self.fields[field]}__{FILTER_LOOKUPS[kind]}': value})
            records = records.exclude(condition) if kind == '!=' else records.filter(condition)
        return records

    def sort(self, records, params):
        order = [
            f"{'-' if sorter.get('dir') == 'desc' else ''}{self.fields[sorter['field']]}"
            for sorter in indexed_params(params, 'sort') if sorter.get('field') in self.fields
        ]
        return records.order_by(*order, f'-{self.model.code_field}')


class RecordStatsAPIView(ApiView):
    """Number of records per group (?by=group) or per operator (?by=operator), after the duty filters."""
    model = None

    def get(self, request):
        records = filter_duty_records(self.model.objects.all(), request.GET)
        by = request.GET.get('by', 'group')
        if by == 'group':
            rows = records.values(group=F('kelompok')).annotate(count=Count('id')).order_by('group')
        elif by == 'operator':
            rows = (records.values('operator_id', operator_name=F('operator__name'))
                    .annotate(count=Count('id')).order_by('-count', 'operator_name'))
        else:
            raise BadRequest("'by' must be 'group' or 'operator'")
        return JsonResponse({'by': by, 'total': records.count(), 'data': list(rows)})


class RecordCsvView(ApiView):
    model = None
    filename = None
    columns = ()  # (header, ORM lookup) pairs

    def get(self, request):
        records = filter_duty_records(self.model.objects.all(), request.GET).order_by(self.model.code_field)
        rows = records.values_list(*(lookup for _, lookup in self.columns)).iterator(chunk_size=500)
        return csv_response(self.filename, [header for header, _ in self.columns], rows)


class RecordExportView(View):
    """One record's filled-in Excel template, as .xlsx or converted to PDF."""
    model = None
    build_workbook = None
    filename = None  # Optional function record -> file name without extension.
    file_format = 'xlsx'

    def get(self, request, pk):
        record = get_object_or_404(self.model.objects.select_related('operator'), pk=pk)
        workbook = self.build_workbook(record)
        filename = self.filename(record) if self.filename else export_filename(record.code)
        if self.file_format == 'pdf':
            return pdf_response(workbook, filename)
        return xlsx_response(workbook, filename)


def parse_duty_query(params):
    """(date, shift codes, group) of a ?date=YYYY-MM-DD[&shift=P|S|M1|M2][&group=N] request."""
    date = parse_date(params.get('date'), 'date')
    code = params.get('shift')
    if code and code not in SHIFT_CODES:
        raise BadRequest(f"'shift' must be one of {', '.join(SHIFT_CODES)}")
    group = parse_int(params['group'], 'group') if params.get('group') else None
    return date, [code] if code else list(SHIFT_CODES), group


def slot_records(job, date, code, group):
    """Records of a job in a duty slot (M2 of a date is the dini hari duty stored under the next date)."""
    record_date, shift = resolve_duty_slot(date, code)
    records = job.model.objects.filter(date=record_date, shift=shift)
    if group is not None:
        records = records.filter(kelompok=group)
    return records.order_by(job.model.code_field)


class DutySummaryAPIView(ApiView):
    """Records of every job done in a duty slot: ?date=YYYY-MM-DD, optional shift (P, S, M1, M2) and group."""

    def get(self, request):
        date, codes, group = parse_duty_query(request.GET)
        return JsonResponse({'date': date, 'group': group, 'slots': [self.slot(date, code, group) for code in codes]})

    @staticmethod
    def slot(date, code, group):
        record_date, shift = resolve_duty_slot(date, code)
        jobs = []
        for job in JOBS:
            if not job.in_shift(shift):
                continue
            rows = slot_records(job, date, code, group).values(
                'id', 'operator_id', group=F('kelompok'), code=F(job.model.code_field), operator_name=F('operator__name'),
            )
            jobs.append({
                'key': job.key,
                'label': job.label,
                'records': [{
                    **row,
                    'edit_url': reverse(job.update_url_name, args=[row['id']]),
                    'xlsx_url': reverse(f'api:{job.api_namespace}:record_xlsx', args=[row['id']]),
                    'pdf_url': reverse(f'api:{job.api_namespace}:record_pdf', args=[row['id']]),
                } for row in rows],
            })
        return {'shift_code': code, 'shift': shift, 'record_date': record_date, 'jobs': jobs}


class ExportError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


class PdfExportView(View):
    """A merged PDF export, opened in a new browser tab from the Rekap page: its errors are an HTML page, not JSON."""

    def dispatch(self, request, *args, **kwargs):
        try:
            return super().dispatch(request, *args, **kwargs)
        except ExportError as error:
            message, status = str(error), error.status
        except BadRequest as error:
            message, status = f'Filter tidak valid: {error}', 400
        return render(request, 'core/export_error.html', {'message': message}, status=status)


def merged_pdf_response(documents, filename):
    try:
        content = documents_to_pdf(documents)
    except (PdfConversionError, subprocess.TimeoutExpired) as error:
        raise ExportError(f'Konversi PDF gagal: {error}', status=500) from error
    return pdf_file_response(content, filename)


def duty_pdf_filename(date, codes, group, record_groups):
    """Serahterima_III_20260913_M2 for one duty (the group in Roman numerals: the chosen one, else the group of its
    records when they share one, else Semua); every duty keeps Rekap_Dinas_2026-09-13_semua[_Kel3]."""
    if len(codes) != 1:
        filename = f'Rekap_Dinas_{date:%Y-%m-%d}_semua'
        return filename + (f'_Kel{group}' if group is not None else '')
    if group is None and len(record_groups) == 1:
        group, = record_groups
    return f"Serahterima_{convert_to_roman(group) if group else 'Semua'}_{date:%Y%m%d}_{codes[0]}"


class DutySummaryPdfView(PdfExportView):
    """Every form of the duty slot(s) in one PDF, in JOBS order: BAST, Peta + PDE, QC-3, QC Focal, Checklist."""

    def get(self, request):
        date, codes, group = parse_duty_query(request.GET)
        documents, record_groups = [], set()
        for code in codes:
            for job in JOBS:
                if not job.in_shift(SHIFT_CODES[code][0]):
                    continue
                for record in slot_records(job, date, code, group).select_related('operator'):
                    record_groups.add(record.kelompok)
                    documents.extend(job.export_documents(record))
        if not documents:
            raise ExportError('Belum ada formulir untuk dinas ini.', status=404)
        return merged_pdf_response(documents, duty_pdf_filename(date, codes, group, record_groups))


class JobRecordsPdfView(PdfExportView):
    """The forms of every record of one job matching the duty filters (group, operator, date_from, date_to, ...)
    in one PDF, ordered by code: the Per Pekerjaan export of the recap page."""

    def get(self, request, key):
        job = next((job for job in JOBS if job.key == key), None)
        if job is None:
            raise ExportError(f"Pekerjaan '{key}' tidak dikenal.", status=404)
        records = filter_duty_records(job.model.objects.select_related('operator'), request.GET)
        count = records.count()
        if not count:
            raise ExportError('Belum ada formulir untuk filter ini.', status=404)
        if count > MAX_EXPORT_RECORDS:
            raise ExportError(f'Terlalu banyak formulir ({count}, maksimal {MAX_EXPORT_RECORDS}); '
                              'persempit tanggal atau filter.')
        documents = [document for record in records.order_by(job.model.code_field)
                     for document in job.export_documents(record)]
        return merged_pdf_response(documents, self.filename(job, request.GET))

    @staticmethod
    def filename(job, params):
        """Checklist_SeisComP_20260913-20260914 (the dates of the filter, when given)."""
        label = '_'.join(re.findall(r'[A-Za-z0-9]+', job.label))
        dates = [parse_date(params[param], param).strftime('%Y%m%d')
                 for param in ('date_from', 'date_to') if params.get(param)]
        return f"{label}_{'-'.join(dates)}" if dates else label


class OperatorListAPIView(ApiView):
    def get(self, request):
        operators = Operator.objects.values('id', 'name', 'nickname', nip=F('NIP'))
        return JsonResponse({'data': list(operators)})


class OperatorDetailAPIView(ApiView):
    def get(self, request, pk):
        operator = get_object_or_404(Operator, pk=pk)
        return JsonResponse({'id': operator.pk, 'name': operator.name, 'nickname': operator.nickname, 'nip': operator.NIP})


class GroupMembersAPIView(ApiView):
    def get(self, request, number):
        kelompok = get_object_or_404(Kelompok, name=number)
        members = [{'id': operator.pk, 'name': operator.name, 'nip': operator.NIP} for operator in kelompok.ordered_members()]
        return JsonResponse({'group': number, 'members': members})
