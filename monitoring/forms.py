from django import forms

from .models import duty_code


class ChecklistRecordForm(forms.ModelForm):
    """Header of a checklist (the answers are posted as '<field>_<row key>', see answers.save_answers)."""

    class Meta:
        fields = ['date', 'shift', 'kelompok', 'operator', 'check_time']
        labels = {'date': 'Hari / Tanggal', 'shift': 'Jadwal Shift', 'operator': 'Analis on Duty',
                  'check_time': 'Waktu Pengecekan (WIB)'}
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}, format='%Y-%m-%d'),
            'shift': forms.Select(attrs={'class': 'form-select'}),
            'kelompok': forms.Select(attrs={'class': 'form-select'}),
            'operator': forms.Select(attrs={'class': 'form-select'}),
            'check_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}, format='%H:%M'),
        }

    def clean(self):
        cleaned_data = super().clean()
        date, shift = cleaned_data.get('date'), cleaned_data.get('shift')
        if date and shift:
            model = self._meta.model
            code = duty_code(model.code_prefix, date, shift)
            if model.objects.filter(**{model.code_field: code}).exclude(pk=self.instance.pk).exists():
                raise forms.ValidationError(f'{code} sudah ada: checklist dinas ini sudah dibuat.')
        return cleaned_data


def checklist_form(model):
    return forms.modelform_factory(model, form=ChecklistRecordForm)
