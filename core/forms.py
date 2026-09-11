from django import forms

from .models import Kelompok, Operator


class OperatorForm(forms.ModelForm):
    class Meta:
        model = Operator
        fields = '__all__'


class KelompokForm(forms.ModelForm):
    # Comma-separated operator ids in display order, kept in sync by kelompok_form.js.
    member = forms.CharField(label='Member')

    class Meta:
        model = Kelompok
        fields = ['name']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.initial['member'] = ','.join(str(operator.pk) for operator in self.instance.ordered_members())

    def clean_member(self):
        ids = [int(pk) for pk in self.cleaned_data['member'].split(',') if pk.strip().isdigit()]
        known = set(Operator.objects.filter(pk__in=ids).values_list('pk', flat=True))
        unknown = [pk for pk in ids if pk not in known]
        if unknown:
            raise forms.ValidationError(f'Petugas tidak ditemukan: {unknown}')
        return ids

    def save(self, commit=True):
        kelompok = super().save(commit=commit)
        if commit:
            kelompok.set_members(self.cleaned_data['member'])
        return kelompok
