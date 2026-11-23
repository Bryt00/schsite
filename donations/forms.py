from django import forms
from main.models import Programme
from .models import Donation, SchoolClass, WasscePayment


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


class WasscePaymentForm(forms.ModelForm):
    class Meta:
        model = WasscePayment
        fields = [
            'surname',
            'other_names',
            'programme',
            'school_class',
            'parent_name',
            'parent_phone',
            'parent_email',
        ]
        widgets = {
            'surname': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': "Ward's Surname (e.g. Mensah)",
                'required': True,
            }),
            'other_names': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': "Ward's Other Names (e.g. Kwame Kofi)",
                'required': True,
            }),
            'programme': forms.Select(attrs={
                'class': 'form-select',
                'id': 'id_programme',
                'required': True,
            }),
            'school_class': forms.Select(attrs={
                'class': 'form-select',
                'id': 'id_school_class',
                'required': True,
            }),
            'parent_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Parent / Guardian Full Name',
            }),
            'parent_phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Parent / Guardian Phone Number (e.g. 024XXXXXXX)',
                'required': True,
            }),
            'parent_email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Parent / Guardian Email (Optional for Receipt)',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['programme'].queryset = Programme.objects.all().order_by('name')
        self.fields['programme'].empty_label = "Select Programme"
        self.fields['school_class'].queryset = SchoolClass.objects.filter(is_active=True).select_related('programme').order_by('sort_order', 'name')
        self.fields['school_class'].empty_label = "Select Class"

    def clean(self):
        cleaned_data = super().clean()
        programme = cleaned_data.get('programme')
        school_class = cleaned_data.get('school_class')
        if programme and school_class and school_class.programme_id and school_class.programme_id != programme.id:
            self.add_error('school_class', f"Selected class '{school_class.name}' does not belong to {programme.name}.")
        return cleaned_data

