"""Indonesian date and number wording used in the Excel/PDF reports."""
import datetime
import re

MONTHS = ('Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni', 'Juli',
          'Agustus', 'September', 'Oktober', 'November', 'Desember')
DAYS = ('Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat', 'Sabtu', 'Minggu')
NUMBER_WORDS = ('Nol', 'Satu', 'Dua', 'Tiga', 'Empat', 'Lima', 'Enam',
                'Tujuh', 'Delapan', 'Sembilan', 'Sepuluh')
ROMAN_NUMERALS = ((1000, 'M'), (900, 'CM'), (500, 'D'), (400, 'CD'), (100, 'C'), (90, 'XC'),
                  (50, 'L'), (40, 'XL'), (10, 'X'), (9, 'IX'), (5, 'V'), (4, 'IV'), (1, 'I'))


def as_date(value):
    """Accept a date or a 'YYYY-MM-DD' string."""
    if isinstance(value, datetime.date):
        return value
    return datetime.datetime.strptime(value, '%Y-%m-%d').date()


def date_from_code(code):
    """Date written in a record code such as 'QC-2025-11-10-4M'."""
    return as_date(re.search(r'\d{4}-\d{2}-\d{2}', code).group())


def format_date_indonesian(value):
    """'2025-11-10' -> '10 November 2025'."""
    date = as_date(value)
    return f'{date.day} {MONTHS[date.month - 1]} {date.year}'


def get_hari_indonesia(value):
    """'2025-11-10' -> 'Senin'."""
    return DAYS[as_date(value).weekday()]


def date_range_to_string(start, end):
    """Two dates as one Indonesian range, e.g. 'Senin - Selasa, 10 - 11 November 2025'."""
    days = f'{DAYS[start.weekday()]} - {DAYS[end.weekday()]}'
    start_month, end_month = MONTHS[start.month - 1], MONTHS[end.month - 1]
    if start.year != end.year and start.month != end.month:
        return f'{days}, {start:%d} {start_month} {start.year} - {end:%d} {end_month} {end.year}'
    if start.month != end.month:
        return f'{days}, {start:%d} {start_month} - {end:%d} {end_month} {start.year}'
    return f'{days}, {start:%d} - {end:%d} {start_month} {start.year}'


def convert_to_roman(number):
    number = int(number)
    roman = ''
    for value, numeral in ROMAN_NUMERALS:
        count, number = divmod(number, value)
        roman += numeral * count
    return roman


def convert_to_indonesian(number):
    number = int(number)
    return NUMBER_WORDS[number] if 0 <= number < len(NUMBER_WORDS) else str(number)
