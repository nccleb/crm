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


class StatisticsQueueForm(forms.Form):
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control',
            'id': 'start_date',
            'placeholder': 'Start date'
        }),
        label='Start Date',
        required=True,
        help_text='Select the beginning date for your statistics report'
    )
    
    end_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control',
            'id': 'end_date',
            'placeholder': 'End date'
        }),
        label='End Date',
        required=True,
        help_text='Select the ending date for your statistics report'
    )
    
    queue_number = forms.CharField(
        widget=forms.TextInput(attrs={
            'type': 'text',
            'class': 'form-control',
            'id': 'queue_number',
            'placeholder': 'Enter queue number'
        }),
        label='Queue Number',
        required=False,
        max_length=50,
        help_text='Optional: Enter specific queue number to filter statistics'
    )
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date:
            if start_date > end_date:
                raise ValidationError("Start date must be before end date.")
        
        return cleaned_data