from django.db import models
from django.utils import timezone
from core.models import User
from characters.models import Character


class Scenario(models.Model):
    """Game scenario/session model"""

    STATUS_CHOICES = [
        ('PLANNING', 'Planning'),
        ('ACTIVE', 'Active'),
        ('PAUSED', 'Paused'),
        ('COMPLETED', 'Completed'),
    ]

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    keeper = models.ForeignKey(User, on_delete=models.CASCADE, related_name='keeper_scenarios')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PLANNING')

    # In-game time
    in_game_time = models.DateTimeField(default=timezone.now)

    # Notes
    public_notes = models.TextField(blank=True)
    keeper_notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} - {self.get_status_display()}"

    class Meta:
        ordering = ['-created_at']


class ScenarioPlayer(models.Model):
    """Players participating in a scenario"""

    scenario = models.ForeignKey(Scenario, on_delete=models.CASCADE, related_name='players')
    player = models.ForeignKey(User, on_delete=models.CASCADE, related_name='player_scenarios')
    character = models.ForeignKey(Character, on_delete=models.SET_NULL, null=True, blank=True)
    joined_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ['scenario', 'player']

    def __str__(self):
        return f"{self.player.username} in {self.scenario.name}"


class ScenarioNPC(models.Model):
    """NPCs present in a scenario"""

    scenario = models.ForeignKey(Scenario, on_delete=models.CASCADE, related_name='npcs')
    npc = models.ForeignKey(Character, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ['scenario', 'npc']

    def __str__(self):
        return f"{self.npc.name} in {self.scenario.name}"


class Invitation(models.Model):
    """Invitations to join scenarios"""

    scenario = models.ForeignKey(Scenario, on_delete=models.CASCADE, related_name='invitations')
    invited_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_invitations')
    invited_player = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_invitations', null=True, blank=True)
    invite_code = models.CharField(max_length=32, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    used_at = models.DateTimeField(null=True, blank=True)
    is_used = models.BooleanField(default=False)

    def __str__(self):
        return f"Invitation to {self.scenario.name}"


class FightEncounter(models.Model):
    """Fight encounters during scenarios"""

    scenario = models.ForeignKey(Scenario, on_delete=models.CASCADE, related_name='encounters')
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    round_number = models.IntegerField(default=1)
    current_turn_index = models.IntegerField(default=0)

    def __str__(self):
        return f"Encounter in {self.scenario.name} - Round {self.round_number}"


class FightParticipant(models.Model):
    """Participants in a fight encounter"""

    encounter = models.ForeignKey(FightEncounter, on_delete=models.CASCADE, related_name='participants')
    character = models.ForeignKey(Character, on_delete=models.CASCADE)
    initiative_order = models.IntegerField()
    is_active = models.BooleanField(default=True)
    dexterity_with_bonus = models.IntegerField()  # DEX + 50 if weapon prepared

    class Meta:
        ordering = ['-dexterity_with_bonus', 'initiative_order']

    def __str__(self):
        return f"{self.character.name} - DEX: {self.dexterity_with_bonus}"


class Message(models.Model):
    """Messages sent from Keeper to players during game"""

    MESSAGE_TYPE_CHOICES = [
        ('PUBLIC', 'Public'),
        ('PRIVATE', 'Private'),
        ('SYSTEM', 'System'),
    ]

    scenario = models.ForeignKey(Scenario, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages', null=True, blank=True)
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPE_CHOICES)
    content = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['-sent_at']

    def __str__(self):
        return f"{self.message_type} message in {self.scenario.name}"