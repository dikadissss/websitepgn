"""Rows of a checklist, shared by the form and the printed sheet: the active catalog for a new record, the saved
answers for an existing one. Posted values are named '<field>_<row key>'."""
from .models import CONFIRM_CHOICES, ChecklistSection

ANSWER_FIELDS = ('access', 'info', 'confirmed', 'forward_to', 'ok')
SECTION_TEXTS = ('heading', 'side_note', 'note', 'note_right')  # Printed from the current catalog.


def _row(key, section_key, section_title, kind, item, name, address, values):
    return {
        'key': key, 'section_key': section_key, 'section_title': section_title, 'kind': kind,
        'item': item, 'name': name, 'address': address, 'password': item.password if item else '',
        **{field: values.get(field) for field in ANSWER_FIELDS},
    }


def catalog_rows(form):
    """One empty row per active item of the form's catalog."""
    rows = []
    for section in ChecklistSection.objects.filter(form=form).prefetch_related('items'):
        for item in section.items.all():
            if item.active:
                rows.append(_row(f'i{item.pk}', section.key, section.title, section.kind, item, item.name,
                                 item.address, {}))
    return rows


def record_rows(record):
    """The saved answers of a record."""
    return [
        _row(f'a{answer.pk}', answer.section_key, answer.section_title, answer.kind, answer.item, answer.item_name,
             answer.item_address, {field: getattr(answer, field) for field in ANSWER_FIELDS if hasattr(answer, field)})
        for answer in record.answers.select_related('item')
    ]


def rows_for(record, model):
    return record_rows(record) if record is not None and record.pk else catalog_rows(model.form)


def group_sections(rows):
    """Rows grouped by section and numbered, with the section's current texts (heading, notes) and answer choices."""
    texts = {section['key']: section for section in ChecklistSection.objects.values(*SECTION_TEXTS, 'key')}
    sections = {}
    for row in rows:
        current = texts.get(row['section_key'], {})
        section = sections.setdefault(row['section_key'], {
            'key': row['section_key'], 'title': row['section_title'], 'kind': row['kind'],
            **{field: current.get(field, '') for field in SECTION_TEXTS},
            'confirm_choices': CONFIRM_CHOICES.get(row['kind'], ()), 'rows': [],
        })
        section['rows'].append({**row, 'no': len(section['rows']) + 1})
    return list(sections.values())


def record_sections(record):
    return group_sections(record_rows(record))


def _clean(answer, field, kind, value):
    value = (value or '').strip()
    if field == 'access':
        return value if value in ('Y', 'N') else ''
    if field == 'confirmed':
        return value if value in dict(CONFIRM_CHOICES.get(kind, ())) else ''
    if field == 'ok':
        return {'ya': True, 'tidak': False}.get(value)
    return value[:answer._meta.get_field(field).max_length]


def save_answers(record, rows, data):
    """Replace the record's answers with the posted values of the rows (built before the record was saved)."""
    model = record.answers.model
    record.answers.all().delete()
    answers = []
    for order, row in enumerate(rows, 1):
        answer = model(record=record, item=row['item'], section_key=row['section_key'],
                       section_title=row['section_title'], kind=row['kind'], order=order, item_name=row['name'],
                       item_address=row['address'])
        for field in ANSWER_FIELDS:
            if hasattr(answer, field):
                setattr(answer, field, _clean(answer, field, row['kind'], data.get(f'{field}_{row["key"]}')))
        answers.append(answer)
    model.objects.bulk_create(answers)
