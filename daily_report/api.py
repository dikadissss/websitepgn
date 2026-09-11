import subprocess
from io import BytesIO

from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST

from core import feeds
from core.api import RecordCsvView, RecordListAPIView, duty_fields, json_errors, parse_date
from core.exports import PdfConversionError, documents_to_pdf, pdf_file_response

from .data import DataNotAvailable, events_table, fetch_day_events, json_records
from .maps import draw_map, render_map
from .models import DailyReport
from .reports import build_map_pdf, export_documents, report_filename


class DailyReportListAPIView(RecordListAPIView):
    model = DailyReport
    fields = {
        **duty_fields('report_id'),
        'report_date': 'report_date',
    }
    search_fields = ('report_id', 'operator__name')


class DailyReportCsvView(RecordCsvView):
    model = DailyReport
    filename = 'daily_report_export.csv'
    columns = (
        ('Report ID', 'report_id'), ('Tanggal Data (UTC)', 'report_date'), ('Tanggal Dinas', 'date'), ('Shift', 'shift'),
        ('Kelompok', 'kelompok'), ('Petugas', 'operator__name'),
    )


@json_errors
def day_events(request):
    """Every event of a UTC day (?date=YYYY-MM-DD) from index3.txt: CSV to store and numbered rows to show."""
    day = parse_date(request.GET.get('date'), 'date')
    try:
        table = fetch_day_events(day)
    except DataNotAvailable as error:
        return JsonResponse({'error': str(error)}, status=404)
    except feeds.FeedError as error:
        return JsonResponse({'error': str(error)}, status=502)
    return JsonResponse({
        'date': day,
        'count': len(table),
        'csv': table.to_csv(index=False),
        'rows': json_records(feeds.numbered(table)),
    })


@require_POST
def redraw_map(request, pk):
    """Plot the map again from the stored events."""
    report = get_object_or_404(DailyReport, pk=pk)
    missing = render_map(report.event_table(), report.map_path)
    return JsonResponse({
        'map_url': f'{report.map_url}?v={int(report.map_path.stat().st_mtime)}',
        'missing_tiles': missing,
    })


@require_POST
def map_preview(request):
    """Map of events not saved yet (the CSV from "Ambil data gempa") as a PNG; nothing is stored."""
    try:
        image, missing = draw_map(events_table(request.POST.get('events', '')))
    except (KeyError, ValueError) as error:
        return JsonResponse({'error': f'Data gempa tidak valid: {error}'}, status=400)
    buffer = BytesIO()
    image.save(buffer, 'PNG')
    response = HttpResponse(buffer.getvalue(), content_type='image/png')
    response['X-Missing-Tiles'] = str(missing)
    return response


def map_pdf(request, pk):
    report = get_object_or_404(DailyReport.objects.select_related('operator'), pk=pk)
    response = HttpResponse(build_map_pdf(report), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename=PetaHarian_{report.report_date:%Y-%m-%d}.pdf'
    return response


def report_pdf(request, pk):
    """PDF export of the report: the Peta Harian page, then the PDE (the same pages as in the Rekap Dinas PDF)."""
    report = get_object_or_404(DailyReport.objects.select_related('operator'), pk=pk)
    try:
        content = documents_to_pdf(export_documents(report))
    except (PdfConversionError, subprocess.TimeoutExpired) as error:
        return HttpResponse(f'PDF conversion failed: {error}', status=500, content_type='text/plain')
    return pdf_file_response(content, report_filename(report))
