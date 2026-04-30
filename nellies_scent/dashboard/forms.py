from django import forms
from django.contrib.sites.models import Site
from django.contrib.auth.models import User
from core.models import Product, Order
from allauth.socialaccount.models import SocialApp


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'description', 'category', 'product_type', 'size', 'price', 'stock', 'image', 'mini_icon']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Product name'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Describe the product'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'product_type': forms.Select(attrs={'class': 'form-control'}),
            'size': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '50ml'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'stock': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control-file'}),
            'mini_icon': forms.ClearableFileInput(attrs={'class': 'form-control-file'}),
        }


class OrderStatusForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['status']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-control'}),
        }


class SiteForm(forms.ModelForm):
    class Meta:
        model = Site
        fields = ['domain', 'name']
        widgets = {
            'domain': forms.TextInput(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
        }


class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'is_active', 'is_staff', 'is_superuser']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_staff': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_superuser': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class SocialAppForm(forms.ModelForm):
    """Form for managing django-allauth SocialApp instances."""
    
    PROVIDER_CHOICES = [
        ('google', 'Google'),
        ('apple', 'Apple'),
        ('facebook', 'Facebook'),
        ('github', 'GitHub'),
        ('linkedin', 'LinkedIn'),
    ]
    
    provider = forms.ChoiceField(
        choices=PROVIDER_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text='Select the OAuth provider for this application.'
    )
    
    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., My Google OAuth App'
        })
    )
    
    client_id = forms.CharField(
        max_length=500,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Client ID from provider'
        })
    )
    
    secret = forms.CharField(
        max_length=500,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Client Secret (keep this secure)'
        }),
        help_text='Your OAuth client secret. Never share this publicly.'
    )
    
    key = forms.CharField(
        max_length=500,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Optional: API key for providers that need it'
        })
    )

    class Meta:
        model = SocialApp
        fields = ['provider', 'name', 'client_id', 'secret', 'key']

    def clean_provider(self):
        provider = self.cleaned_data['provider']
        
        # Check for duplicate provider
        if self.instance.pk is None:  # Creating new instance
            if SocialApp.objects.filter(provider=provider).exists():
                raise forms.ValidationError(
                    f'A social app for {provider.title()} already exists. Only one app per provider is allowed.'
                )
        else:  # Editing existing instance
            if SocialApp.objects.filter(provider=provider).exclude(pk=self.instance.pk).exists():
                raise forms.ValidationError(
                    f'A social app for {provider.title()} already exists. Only one app per provider is allowed.'
                )
        
        return provider

    def clean_client_id(self):
        client_id = self.cleaned_data.get('client_id')
        if not client_id or not client_id.strip():
            raise forms.ValidationError('Client ID cannot be empty.')
        return client_id

    def clean_secret(self):
        secret = self.cleaned_data.get('secret')
        if not secret or not secret.strip():
            raise forms.ValidationError('Secret key cannot be empty.')
        return secret

    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Ensure the app is attached to SITE_ID = 1
        if commit:
            instance.save()
            # Attach to default site
            from django.conf import settings
            site_id = getattr(settings, 'SITE_ID', 1)
            site = Site.objects.get(pk=site_id)
            instance.sites.add(site)
        
        return instance
