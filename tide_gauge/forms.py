from django import forms

from monitoring.forms import ChecklistRecordForm

from . import feed
from .models import TideGaugeRecord

STATION_TEXTS = {'code': 30, 'location': 200, 'region': 100}  # Text fields of a station and their maximum length.


class TideGaugeRecordForm(ChecklistRecordForm):
    """Header of the checklist (one per duty, see ChecklistRecordForm.clean) and the stations, which the page posts
    as JSON after "Ambil data Tide Gauge" and the officer's changes."""
    stations = forms.JSONField(widget=forms.HiddenInput, required=False)

    class Meta(ChecklistRecordForm.Meta):
        model = TideGaugeRecord
        fields = [*ChecklistRecordForm.Meta.fields, 'web_accessible', 'data_time', 'stations']
        labels = {**ChecklistRecordForm.Meta.labels, 'operator': 'Operator on Duty',
                  'web_accessible': 'Web Tide Gauge bisa diakses'}
        widgets = {**ChecklistRecordForm.Meta.widgets,
                   'web_accessible': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
                   'data_time': forms.HiddenInput}

    def clean_stations(self):
        stations = self.cleaned_data.get('stations') or []
        if not isinstance(stations, list):
            raise forms.ValidationError('Data stasiun tidak valid.')
        return [self._station(station) for station in stations]

    @staticmethod
    def _station(station):
        if (not isinstance(station, dict) or station.get('net') not in feed.CATEGORY_NAMES
                or station.get('status') not in feed.STATUSES):
            raise forms.ValidationError('Data stasiun tidak valid: jaringan atau status tidak dikenal.')
        latency = station.get('latency')
        if isinstance(latency, bool) or not isinstance(latency, (int, float)):
            latency = None
        return {'net': station['net'],
                **{field: str(station.get(field) or '-')[:length] for field, length in STATION_TEXTS.items()},
                'latency': latency, 'status': station['status']}

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('web_accessible') and not cleaned_data.get('stations') and 'stations' not in self.errors:
            raise forms.ValidationError('Klik "Ambil data Tide Gauge" dulu, atau hilangkan centang "Web Tide Gauge '
                                        'bisa diakses" bila web tidak bisa diakses.')
        return cleaned_data
