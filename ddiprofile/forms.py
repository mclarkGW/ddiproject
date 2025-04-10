from django import forms
from .models import DDIProfile, DDIStatus

class DDIProfileForm(forms.ModelForm):
    start_date =forms.DateField(widget=forms.DateInput(attrs={'type':'date'}))
    sit_start_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    sit_end_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    uat_start_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    uat_end_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    go_live_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    class Meta:
        model = DDIProfile
        fields = '__all__'

class DDIStatusForm(forms.ModelForm):
    date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    class Meta:
        model = DDIStatus
        fields = '__all__'
