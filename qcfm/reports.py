from pathlib import Path

import openpyxl

from core.reports import fill_qc_sheet

TEMPLATE_PATH = Path(__file__).resolve().parent / 'static' / 'qcfm' / 'QC_FM.xlsx'


def export_documents(record):
    """Documents printed for the record, in order (see core.duty.JOBS)."""
    return [build_workbook(record)]


def build_workbook(record):
    workbook = openpyxl.load_workbook(TEMPLATE_PATH)
    sheet = workbook.active
    sheet.title = 'QC Records'
    fill_qc_sheet(sheet, record, record.qcfm_prev, record.qcfm, 'QCFM', table_width=17)
    return workbook
