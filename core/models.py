from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Custom user model with role management"""

    class Role(models.TextChoices):
        PLAYER = 'PLAYER', 'Player'
        KEEPER = 'KEEPER', 'Keeper'

    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.PLAYER,
    )

    def is_keeper(self):
        return self.role == self.Role.KEEPER

    def is_player(self):
        return self.role == self.Role.PLAYER
