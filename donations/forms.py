from django import forms
from .models import Donation

class DonationForm(forms.ModelForm):
    class Meta:
        model = Donation
        fields = ['donor_name', 'donor_email', 'amount', 'cause']
        widgets = {
            'donor_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your Name'}),
            'donor_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Your Email'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Amount (GHS)'}),
            'cause': forms.Select(attrs={'class': 'form-control'}),
        }
