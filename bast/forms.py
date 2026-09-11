from django import forms

from .models import BastRecordModel


class BastRecordForm(forms.ModelForm):
    bast_id = forms.CharField()

    class Meta:
        model = BastRecordModel
        fields = [
            'date', 'bast_id', 'waktu_pelaksanaan', 'shift', 'kelompok', 'kel_berikut', 'operator', 'spv', 'NIP',
            'events', 'event_indonesia', 'event_luar', 'event_dirasakan', 'event_dikirim', 'member',
            'count_gaps', 'count_spikes', 'count_blanks', 'waktu_cs', 'pulsa_poco', 'poco_exp', 'samsung_exp', 'notes',
        ]
        labels = {'operator': 'Petugas', 'spv': 'SPV'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Optional in the database only because old BASTs have no officer; every new BAST needs one.
        self.fields['operator'].required = True
