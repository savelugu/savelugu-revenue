from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import Payment,Business

from django.contrib.auth.forms import UserCreationForm
from core.models import User  # or your custom user model


class PaymentForm(forms.ModelForm):
    paystack_reference = forms.CharField(widget=forms.HiddenInput(), required=False)
    latitude = forms.DecimalField(widget=forms.TextInput(attrs={'readonly': 'readonly'}), required=False)
    longitude = forms.DecimalField(widget=forms.TextInput(attrs={'readonly': 'readonly'}), required=False)


    class Meta:
        model = Payment
        fields = [
            'full_name', 'amount', 'method', 'igf_type',
            'business', 'paystack_reference', 'latitude', 'longitude'
        ]
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'method': forms.Select(attrs={
                'class': 'form-control',
                'onchange': 'togglePaystack(this.value)'
            }),
            'igf_type': forms.Select(attrs={'class': 'form-control'}),
            'business': forms.Select(attrs={'class': 'form-control'}),
        }


class CustomLoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={'placeholder': 'Username', 'class': 'form-control'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Password', 'class': 'form-control'})
    )

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        # Optional: restrict login if role is not allowed
        if user.role not in ['collector', 'admin', 'business']:
            raise forms.ValidationError(
                "Your account role does not have access.",
                code='invalid_role'
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



from django import forms
from .models import BusinessOwner
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from .models import BusinessOwner

class BusinessOwnerForm(forms.ModelForm):
    class Meta:
        model = BusinessOwner
        fields = ['phone_number','business_name', 'location', 'latitude', 'longitude']
        widgets = {
            'latitude': forms.HiddenInput(attrs={'id': 'latitude'}),
            'longitude': forms.HiddenInput(attrs={'id': 'longitude'}),
        }

User = get_user_model()

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.validators import RegexValidator
from .models import User  # Your custom user model
from .models import BusinessOwner  # Assuming you're linking signup to a BusinessOwner profile

class BusinessOwnerSignupForm(UserCreationForm):
    business_name = forms.CharField(
        max_length=255,
        label="Business Name",
        widget=forms.TextInput(attrs={'placeholder': 'e.g. Savelugu Ventures'})
    )

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'placeholder': 'you@example.com'})
    )

    phone_number = forms.CharField(
        max_length=20,
        validators=[RegexValidator(r'^\+?\d{9,15}$', message="Enter a valid phone number.")],
        widget=forms.TextInput(attrs={'placeholder': '+233xxxxxxxxx'})
    )

    location = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={'placeholder': 'Business location'})
    )

    latitude = forms.FloatField(
        required=False,
        widget=forms.HiddenInput(attrs={'id': 'latitude'})
    )

    longitude = forms.FloatField(
        required=False,
        widget=forms.HiddenInput(attrs={'id': 'longitude'})
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'phone_number', 'password1', 'password2']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'business'
        user.email = self.cleaned_data['email']
        user.phone_number = self.cleaned_data['phone_number']
        if commit:
            user.save()
            BusinessOwner.objects.create(
                user=user,
                business_name=self.cleaned_data['business_name'],
                phone_number=self.cleaned_data['phone_number'],
                location=self.cleaned_data['location'],
                latitude=self.cleaned_data['latitude'],
                longitude=self.cleaned_data['longitude']
            )
        return user


class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'email','role', 'password1', 'password2']



class BusinessCheckForm(forms.Form):
    phone_number = forms.CharField(label="Phone Number", max_length=15)


from django import forms
from .models import BusinessPayment

class BusinessPaymentForm(forms.ModelForm):
    class Meta:
        model = BusinessPayment
        fields = ['amount', 'full_name']  # Add more if needed


from django import forms
from .models import BusinessOwnerPayment

class BusinessOwnerPaymentForm(forms.ModelForm):
    class Meta:
        model = BusinessOwnerPayment
        fields = [
            'full_name',
            'amount',
            'igf_type',
            'business',
            'latitude',
            'longitude',
        ]
        widgets = {
            'full_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter business owner name'
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Amount in GHS'
            }),
            'igf_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'business': forms.Select(attrs={
                'class': 'form-select'
            }),
            'latitude': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.000001',
                'placeholder': 'Latitude (optional)'
            }),
            'longitude': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.000001',
                'placeholder': 'Longitude (optional)'
            }),
        }

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount <= 0:
            raise forms.ValidationError("Amount must be greater than zero.")
        return amount


from django import forms
from django.contrib.auth.forms import AuthenticationForm

class BusinessOwnerLoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'placeholder': 'Username',
            'class': 'form-control',
            'autocomplete': 'username'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Password',
            'class': 'form-control',
            'autocomplete': 'current-password'
        })
    )
