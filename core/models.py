from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    """Custom user model with role management"""

    class Role(models.TextChoices):
        PLAYER = 'PLAYER', _('Player')
        KEEPER = 'KEEPER', _('Keeper')

    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.PLAYER,
    )

    def is_keeper(self):
        return self.role == self.Role.KEEPER

    def is_player(self):
        return self.role == self.Role.PLAYER
