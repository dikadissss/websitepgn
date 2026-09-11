"""HTTP responses for the record exports: filled-in Excel templates, their PDF version and CSV dumps."""
import csv
import re
import shutil
import subprocess
import tempfile
from io import BytesIO
from pathlib import Path

from django.http import HttpResponse, StreamingHttpResponse
from pypdf import PdfWriter

XLSX_CONTENT_TYPE = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
PDF_CONVERSION_TIMEOUT = 120


class PdfConversionError(Exception):
    pass


def export_filename(code):
    """'QC-2025-11-10-4M' -> 'QC-2025-11-10-M' (the order digit is only there for sorting)."""
    return re.sub(r'-(\d)([DPSM])$', r'-\2', code)


def xlsx_response(workbook, filename):
    response = HttpResponse(content_type=XLSX_CONTENT_TYPE)
    response['Content-Disposition'] = f'attachment; filename={filename}.xlsx'
    workbook.save(response)
    return response


def convert_to_pdf(workbooks):
    """PDF bytes of each workbook, converted by a single headless LibreOffice run in a private temporary directory."""
    soffice = shutil.which('soffice') or shutil.which('libreoffice')
    if not soffice:
        raise PdfConversionError('LibreOffice (soffice) is not installed or not in PATH.')

    with tempfile.TemporaryDirectory(prefix='ebast-') as workdir:
        xlsx_paths = []
        for index, workbook in enumerate(workbooks):
            path = Path(workdir) / f'{index:03d}.xlsx'
            workbook.save(path)
            xlsx_paths.append(path)
        result = subprocess.run(
            [soffice, '--headless', '--convert-to', 'pdf:calc_pdf_Export', *map(str, xlsx_paths), '--outdir', workdir],
            capture_output=True, timeout=PDF_CONVERSION_TIMEOUT * len(xlsx_paths),
        )
        pdf_paths = [path.with_suffix('.pdf') for path in xlsx_paths]
        if result.returncode != 0 or not all(path.exists() for path in pdf_paths):
            raise PdfConversionError(result.stderr.decode(errors='replace') or 'no PDF produced')
        return [path.read_bytes() for path in pdf_paths]


def merge_pdfs(documents):
    """One PDF with the pages of every document (PDF bytes), in order."""
    writer = PdfWriter()
    for document in documents:
        writer.append(BytesIO(document))
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def pdf_file_response(content, filename):
    response = HttpResponse(content, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename={filename}.pdf'
    return response


def pdf_response(workbook, filename):
    try:
        pdf, = convert_to_pdf([workbook])
    except (PdfConversionError, subprocess.TimeoutExpired) as error:
        return HttpResponse(f'PDF conversion failed: {error}', status=500, content_type='text/plain')
    return pdf_file_response(pdf, filename)


class _Echo:
    """File-like object whose write() hands the formatted CSV line back to the generator."""

    def write(self, value):
        return value


def csv_response(filename, header, rows):
    """Stream rows as CSV (with a BOM so Excel detects UTF-8) without building the file in memory."""
    writer = csv.writer(_Echo(), quoting=csv.QUOTE_ALL)

    def lines():
        yield '﻿'
        yield writer.writerow(header)
        for row in rows:
            yield writer.writerow(row)

    response = StreamingHttpResponse(lines(), content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return response
