from django import forms

from .models import Lead, Comment, LeadFile

class AddLeadForm(forms.ModelForm):
    class Meta:
        model = Lead
        fields = ('name', 'phone_number','email', 'description', 'priority', 'status',)


class AddCommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ('content',)

class AddFileForm(forms.ModelForm):
    class Meta:
        model = LeadFile
        fields = ('file',)       