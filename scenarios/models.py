from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from core.models import User
from characters.models import Character, NPCTemplate


class Scenario(models.Model):
    """Game scenario/session model"""

    STATUS_CHOICES = [
        ('PLANNING', _('Not Started')),
        ('ACTIVE', _('Ongoing')),
        ('PAUSED', _('Paused')),
        ('COMPLETED', _('Done')),
    ]

    VISIBILITY_CHOICES = [
        ('PRIVATE', _('Private')),
        ('PUBLIC', _('Public')),
    ]

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    place = models.CharField(max_length=200, blank=True)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    visibility = models.CharField(max_length=10, choices=VISIBILITY_CHOICES, default='PRIVATE')
    keeper = models.ForeignKey(User, on_delete=models.CASCADE, related_name='keeper_scenarios')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PLANNING')

    # In-game time
    in_game_time = models.DateTimeField(default=timezone.now)
    in_game_day = models.PositiveIntegerField(default=1)

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
    private_notes = models.TextField(blank=True)
    joined_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ['scenario', 'player']

    def __str__(self):
        return f"{self.player.username} in {self.scenario.name}"


class ScenarioNPC(models.Model):
    """NPCs present in a scenario"""

    scenario = models.ForeignKey(Scenario, on_delete=models.CASCADE, related_name='npcs')
    npc = models.ForeignKey(Character, on_delete=models.CASCADE, related_name='scenario_appearances')
    display_name = models.CharField(max_length=200, blank=True,
                                    help_text="Override NPC name for this scenario (e.g. 'Zombie #2')")
    source_template = models.ForeignKey(NPCTemplate, on_delete=models.SET_NULL, null=True, blank=True,
                                        help_text="Template used to create this NPC")
    is_active = models.BooleanField(default=True)

    def get_display_name(self):
        return self.display_name or self.npc.name

    def __str__(self):
        return f"{self.get_display_name()} in {self.scenario.name}"


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


class Hint(models.Model):
    """Reusable gameplay hints shown to players or keepers."""

    AUDIENCE_PLAYER = 'PLAYER'
    AUDIENCE_KEEPER = 'KEEPER'
    AUDIENCE_CHOICES = [
        (AUDIENCE_PLAYER, _('Player')),
        (AUDIENCE_KEEPER, _('Keeper')),
    ]

    title = models.CharField(max_length=120, blank=True)
    text = models.TextField()
    audience = models.CharField(max_length=10, choices=AUDIENCE_CHOICES)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['audience', 'sort_order', 'id']

    def __str__(self):
        label = self.title or self.text[:40]
        return f"{self.get_audience_display()}: {label}"


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
    is_weapon_prepared = models.BooleanField(default=False)
    dexterity_with_bonus = models.IntegerField()  # Effective DEX (doubled when weapon is prepared)

    class Meta:
        ordering = ['-dexterity_with_bonus', 'initiative_order']

    def __str__(self):
        return f"{self.character.name} - DEX: {self.dexterity_with_bonus}"


class Message(models.Model):
    """Messages sent from Keeper to players during game"""

    MESSAGE_TYPE_CHOICES = [
        ('PUBLIC', _('Public')),
        ('PRIVATE', _('Private')),
        ('SYSTEM', _('System')),
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


class MessageReceipt(models.Model):
    """Per-user delivery/read tracking for scenario messages."""

    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='receipts')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='message_receipts')
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-message__sent_at', '-created_at']
        unique_together = ['message', 'user']

    def __str__(self):
        return f"Receipt for {self.user.username} - {self.message_id}"
