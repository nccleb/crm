from django import forms
from django.core.exceptions import ValidationError
from datetime import datetime

class StatisticsForm(forms.Form):
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control',
            'id': 'sta',
            'placeholder': 'start time'
        }),
        label='Start Date',
        required=True
    )
    
    end_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control',
            'id': 'end',
            'placeholder': 'end time'
        }),
        label='End Date',
        required=True
    )
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date:
            if start_date > end_date:
                raise ValidationError("Start date must be before end date.")
        
        return cleaned_data