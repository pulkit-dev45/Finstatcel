import re
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import get_user_model

User = get_user_model()

BANK_CHOICES = [
    ('auto', 'Auto Detect'),
    ('sbi', 'State Bank of India (SBI)'),
    ('axis', 'Axis Bank'),
    ('hdfc', 'HDFC Bank'),
    ('icici', 'ICICI Bank'),
    ('kotak', 'Kotak Mahindra'),
    ('pnb', 'Punjab National Bank'),
    ('bob', 'Bank of Baroda'),
    ('canara', 'Canara Bank'),
    ('uco', 'UCO Bank'),
    ('other', 'Other Bank'),
]


class StatementUploadForm(forms.Form):
    bank_name = forms.ChoiceField(
        choices=BANK_CHOICES,
        initial='auto',
        label='Select your bank',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    pdf_file = forms.FileField(
        label='Upload PDF statement',
        widget=forms.FileInput(attrs={'accept': '.pdf', 'class': 'form-control'})
    )


class RegisterForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'you@example.com',
        })
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in ('username', 'password1', 'password2'):
            self.fields[field_name].widget.attrs.update({
                'class': 'form-control form-control-lg',
            })
        self.fields['username'].widget.attrs['placeholder'] = 'Choose a username'
        self.fields['password1'].widget.attrs['placeholder'] = 'Create a strong password'
        self.fields['password2'].widget.attrs['placeholder'] = 'Confirm your password'

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError('This username is already taken. Please choose another.')
        if len(username) < 3:
            raise forms.ValidationError('Username must be at least 3 characters.')
        if not re.match(r'^[\w.@+-]+$', username):
            raise forms.ValidationError('Username contains invalid characters.')
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

    def clean_password1(self):
        password = self.cleaned_data.get('password1')
        if len(password) < 8:
            raise forms.ValidationError('Password must be at least 8 characters.')
        return password

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError('Passwords do not match.')
        return cleaned_data


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Username or Email',
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Enter your password',
        })
    )
