import datetime
from pathlib import Path

import openpyxl
from openpyxl.drawing.image import Image
from openpyxl.drawing.spreadsheet_drawing import AnchorMarker, OneCellAnchor
from openpyxl.drawing.xdr import XDRPositiveSize2D
from openpyxl.utils import get_column_letter
from openpyxl.utils.units import pixels_to_EMU

from core.dates import date_from_code, date_range_to_string, format_date_indonesian, get_hari_indonesia

TEMPLATE_PATH = Path(__file__).resolve().parent / 'static' / 'cl_seiscomp' / 'cl_seiscomp.xlsx'
# The map on the slmon sheet: at most this size in pixels (aspect ratio kept), nearly the width of columns A-P.
SLMON_IMAGE_BOX = (1300, 626)
SLMON_COLUMNS = 16        # A-P: the title is merged over A1:P1 and the map is centered under it.
SLMON_IMAGE_ROW = 2       # Row 3 (zero-based).
SLMON_SIGNATURE_ROW = 24  # First row of the template's signature block ('Petugas on Duty', 'Jakarta, ...').
SLMON_EXTRA_ROWS = 13     # Rows inserted above the signatures so the larger map fits (rows of 19.2 px).
DEFAULT_COLUMN_WIDTH = 8.43
LIBREOFFICE_PIXELS_PER_CHARACTER = 8.42


def export_documents(record):
    """Documents printed for the record, in order (see core.duty.JOBS)."""
    return [build_workbook(record)]


def build_workbook(record):
    workbook = openpyxl.load_workbook(TEMPLATE_PATH)
    record_date = date_from_code(record.cs_id)
    # The Malam checklist runs past midnight, so its report covers two days.
    is_night = record.shift.upper() == 'MALAM'
    _fill_checklist(workbook['checklist_seiscomp'], record, record_date, is_night)
    _fill_slmon(workbook['slmon'], record, record_date + datetime.timedelta(days=1) if is_night else record_date)
    return workbook


def _fill_checklist(sheet, record, record_date, is_night):
    sheet.title = 'Checklist Seiscomp'
    if is_night:
        sheet['R3'] = date_range_to_string(record_date, record_date + datetime.timedelta(days=1))
    else:
        sheet['R3'] = f'{get_hari_indonesia(record_date)}, {format_date_indonesian(record_date)}'
    sheet['A3'] = f'KELOMPOK: {record.kelompok}'
    sheet['A2'] = f'SHIFT {record.shift.upper()}'
    sheet['H286'] = f'{record.operator}'
    sheet['D5'] = sheet['P5'] = sheet['H276'] = f'JAM {record.jam_pelaksanaan}'

    stations = [set((text or '').splitlines()) for text in (record.gaps, record.spikes, record.blanks)]
    # Station codes are listed in two blocks; mark gaps/spikes/blanks next to each code.
    _mark_stations(sheet, code_column=2, last_row=287, mark_columns=(4, 5, 6), stations=stations)
    _mark_stations(sheet, code_column=9, last_row=274, mark_columns=(16, 17, 18), stations=stations)

    # Print columns A-R at one page width: the template's fixed 64 % scale pushed the right block to extra pages.
    sheet.print_area = 'A1:R287'
    sheet.sheet_properties.pageSetUpPr.fitToPage = True
    sheet.page_setup.fitToWidth = 1
    sheet.page_setup.fitToHeight = 0


def _mark_stations(sheet, code_column, last_row, mark_columns, stations):
    for row in range(7, last_row + 1):
        code = sheet.cell(row=row, column=code_column).value
        for column, codes in zip(mark_columns, stations):
            if code in codes:
                sheet.cell(row=row, column=column).value = 1


def _fill_slmon(sheet, record, report_date):
    # Room for the larger map: the signature block moves down.
    sheet.insert_rows(SLMON_SIGNATURE_ROW, SLMON_EXTRA_ROWS)
    signature_row = SLMON_SIGNATURE_ROW + SLMON_EXTRA_ROWS
    tanggal = format_date_indonesian(report_date)
    sheet['A2'] = f'{tanggal}, pukul {record.jam_pelaksanaan}'
    sheet[f'M{signature_row}'] = f'Jakarta, {tanggal}'
    sheet[f'C{signature_row + 4}'] = f'{record.operator}'

    # One page, with columns A-P (title and map) centered on it.
    sheet.print_area = f'A1:{get_column_letter(SLMON_COLUMNS)}{sheet.max_row}'
    sheet.print_options.horizontalCentered = True
    sheet.page_setup.fitToWidth = sheet.page_setup.fitToHeight = 1

    if not record.slmon_image:
        sheet['B3'] = 'No image'
        return
    try:
        image = Image(record.slmon_image.path)
    except FileNotFoundError:
        sheet['B3'] = 'Image file not found'
        return
    image.width, image.height = fit_size((image.width, image.height), SLMON_IMAGE_BOX)
    image.anchor = centered_anchor(sheet, (image.width, image.height), SLMON_IMAGE_ROW, SLMON_COLUMNS)
    if sheet._images:
        sheet._images[0] = image
    else:
        sheet.add_image(image)


def fit_size(size, box):
    """The largest size within box with the aspect ratio of size."""
    scale = min(box[0] / size[0], box[1] / size[1])
    return round(size[0] * scale), round(size[1] * scale)


def column_pixels(sheet, column):
    """Width of a column in pixels as LibreOffice, which makes the PDF, lays it out (measured on this template:
    a 13-character column is about 109.5 px, not the 96 px of Excel)."""
    width = sheet.column_dimensions[get_column_letter(column)].width or DEFAULT_COLUMN_WIDTH
    return round(width * LIBREOFFICE_PIXELS_PER_CHARACTER)


def centered_anchor(sheet, size, row, columns):
    """Anchor of an image of size (width, height) pixels, centered across the first columns of the sheet."""
    width, height = size
    widths = [column_pixels(sheet, column) for column in range(1, columns + 1)]
    left, column = max((sum(widths) - width) / 2, 0), 0
    while column < len(widths) - 1 and left >= widths[column]:
        left -= widths[column]
        column += 1
    marker = AnchorMarker(col=column, colOff=pixels_to_EMU(left), row=row, rowOff=0)
    return OneCellAnchor(_from=marker, ext=XDRPositiveSize2D(pixels_to_EMU(width), pixels_to_EMU(height)))
