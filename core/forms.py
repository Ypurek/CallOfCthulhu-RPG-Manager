from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm


class CustomUserCreationForm(UserCreationForm):
    """Registration form bound to the active AUTH_USER_MODEL."""

    class Meta:
        model = get_user_model()
        fields = ("username",)


