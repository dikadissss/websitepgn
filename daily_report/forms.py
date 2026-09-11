import datetime

from django import forms

from core import feeds

from .data import DataNotAvailable, fetch_day_events
from .models import DailyReport


def yesterday_utc():
    return datetime.datetime.now(datetime.timezone.utc).date() - datetime.timedelta(days=1)


class DailyReportForm(forms.ModelForm):
    class Meta:
        model = DailyReport
        fields = ['report_date', 'kelompok', 'operator', 'events']
        labels = {'report_date': 'Tanggal data gempa (UTC)', 'operator': 'Petugas onduty'}
        widgets = {
            'report_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}, format='%Y-%m-%d'),
            'kelompok': forms.Select(attrs={'class': 'form-select'}),
            'operator': forms.Select(attrs={'class': 'form-select'}),
            'events': forms.HiddenInput,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.initial.setdefault('report_date', yesterday_utc())

    def clean(self):
        cleaned_data = super().clean()
        report_date = cleaned_data.get('report_date')
        if report_date and not cleaned_data.get('events', '').strip():
            # "Ambil data gempa" was not pressed: take the day's events from the feed now.
            try:
                cleaned_data['events'] = fetch_day_events(report_date).to_csv(index=False)
            except (DataNotAvailable, feeds.FeedError) as error:
                raise forms.ValidationError(f'Data gempa tidak bisa diambil: {error}') from error
        return cleaned_data
