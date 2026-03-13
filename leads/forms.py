from __future__ import annotations

from django import forms

from .models import Lead, Manager, PipelineStatus


class LeadForm(forms.ModelForm):
    class Meta:
        model = Lead
        fields = ["lead_id", "source", "manager", "amount", "current_status"]
        widgets = {
            "lead_id": forms.TextInput(attrs={"class": "form-control"}),
            "source": forms.TextInput(attrs={"class": "form-control"}),
            "manager": forms.Select(attrs={"class": "form-select"}),
            "amount": forms.NumberInput(attrs={"class": "form-control", "min": "0", "step": "0.01"}),
            "current_status": forms.Select(attrs={"class": "form-select"}),
        }


class StatusChangeForm(forms.Form):
    status = forms.ModelChoiceField(
        queryset=PipelineStatus.objects.all(),
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    changed_by = forms.ModelChoiceField(
        label="Кем изменён",
        queryset=Manager.objects.all(),
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    comment = forms.CharField(
        label="Комментарий",
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 2}),
    )


class CsvImportForm(forms.Form):
    file = forms.FileField(label="CSV файл", widget=forms.ClearableFileInput(attrs={"class": "form-control"}))

