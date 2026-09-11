from django import forms
from django.contrib import admin

from .models import ChecklistItem, ChecklistSection


class ChecklistItemForm(forms.ModelForm):
    class Meta:
        model = ChecklistItem
        fields = '__all__'
        widgets = {'password': forms.PasswordInput(render_value=True)}


class ChecklistItemInline(admin.TabularInline):
    model = ChecklistItem
    form = ChecklistItemForm
    extra = 0


@admin.register(ChecklistSection)
class ChecklistSectionAdmin(admin.ModelAdmin):
    list_display = ('title', 'form', 'kind', 'order')
    list_filter = ('form',)
    ordering = ('form', 'order')
    inlines = [ChecklistItemInline]
