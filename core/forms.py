from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import Payment,Business

class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['business', 'amount', 'method', 'location']
        widgets = {
            'method': forms.Select(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
        }

class CustomLoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={'placeholder': 'Username', 'class': 'form-control'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Password', 'class': 'form-control'})
    )

class BusinessForm(forms.ModelForm):
    class Meta:
        model = Business
        fields = ['name', 'phone_number', 'location', 'latitude', 'longitude']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Business Name'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Location'}),
            'latitude': forms.HiddenInput(attrs={'id': 'latitude'}),
            'longitude': forms.HiddenInput(attrs={'id': 'longitude'}),
        }
