from pathlib import Path

import openpyxl

from core.reports import fill_qc_sheet

TEMPLATE_PATH = Path(__file__).resolve().parent / 'static' / 'qc' / 'QC Seiscomp.xlsx'


def export_documents(record):
    """Documents printed for the record, in order (see core.duty.JOBS)."""
    return [build_workbook(record)]


def build_workbook(record):
    workbook = openpyxl.load_workbook(TEMPLATE_PATH)
    sheet = workbook.active
    sheet.title = 'QC Records'
    sheet['B6'] = f'Event di Indonesia: {record.event_indonesia}'
    sheet['G6'] = f'Event di Luar Negeri: {record.event_luar}'
    fill_qc_sheet(sheet, record, record.qc_prev, record.qc, 'QC', table_width=13, left_aligned_column=13)
    return workbook
