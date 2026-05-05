from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordChangeForm, UserCreationForm


class CustomUserCreationForm(UserCreationForm):
    """Registration form bound to the active AUTH_USER_MODEL."""

    class Meta:
        model = get_user_model()
        fields = ("username",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap styling to form fields
        for field_name, field in self.fields.items():
            field.widget.attrs.update({
                'class': 'form-control',
                'placeholder': field.label,
            })
            # Add specific attributes for password fields
            if 'password' in field_name:
                field.widget.attrs.update({
                    'type': 'password',
                    'autocomplete': 'off',
                })


class AuthenticationForm(forms.Form):
    """Custom login form with Bootstrap styling"""
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ім\'я користувача',
            'autocomplete': 'username',
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Пароль',
            'autocomplete': 'current-password',
        })
    )


class ProfilePasswordChangeForm(PasswordChangeForm):
    """Password change form styled for the profile page."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        placeholders = {
            'old_password': 'Поточний пароль',
            'new_password1': 'Новий пароль',
            'new_password2': 'Підтвердити новий пароль',
        }
        autocomplete = {
            'old_password': 'current-password',
            'new_password1': 'new-password',
            'new_password2': 'new-password',
        }
        for field_name, field in self.fields.items():
            field.widget.attrs.update({
                'class': 'form-control',
                'placeholder': placeholders.get(field_name, field.label),
                'autocomplete': autocomplete.get(field_name, 'off'),
            })


