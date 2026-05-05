from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.utils.translation import gettext_lazy as _, gettext
from core.models import User


class Character(models.Model):
    """Character model for both PCs and NPCs"""

    CHARACTER_TYPE_CHOICES = [
        ('PC', _('Player Character')),
        ('NPC', _('Non-Player Character')),
    ]

    # Ownership and type
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='characters')
    character_type = models.CharField(max_length=3, choices=CHARACTER_TYPE_CHOICES, default='PC')
    is_alive = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Basic info
    name = models.CharField(max_length=100)
    birthplace = models.CharField(max_length=100, blank=True)
    residence = models.CharField(max_length=100, blank=True)
    occupation = models.CharField(max_length=100, blank=True)
    gender = models.CharField(max_length=20, blank=True)
    age = models.IntegerField(null=True, blank=True)
    description = models.TextField(blank=True)

    # Characteristics (0–100 for PCs; NPCs may exceed 100 – enforced at the view layer)
    strength = models.IntegerField(validators=[MinValueValidator(0)])
    constitution = models.IntegerField(validators=[MinValueValidator(0)])
    dexterity = models.IntegerField(validators=[MinValueValidator(0)])
    intelligence = models.IntegerField(validators=[MinValueValidator(0)])
    power = models.IntegerField(validators=[MinValueValidator(0)])
    size = models.IntegerField(validators=[MinValueValidator(0)])
    appearance = models.IntegerField(validators=[MinValueValidator(0)])
    education = models.IntegerField(validators=[MinValueValidator(0)])

    # Status
    hp_current = models.IntegerField()
    hp_max = models.IntegerField()
    mp_current = models.IntegerField()
    mp_max = models.IntegerField()
    sanity_current = models.IntegerField()
    sanity_max = models.IntegerField()
    sanity_start = models.IntegerField()
    luck = models.IntegerField(validators=[MinValueValidator(0)])

    # Derived values
    movement = models.IntegerField(default=9)
    build = models.IntegerField()
    damage_bonus = models.CharField(max_length=10)
    cash = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Notes
    player_notes = models.TextField(blank=True)
    keeper_notes = models.TextField(blank=True)

    def calculate_hp_max(self):
        return (self.strength + self.constitution) // 10

    def calculate_mp_max(self):
        return self.power // 5

    def calculate_build(self):
        total = self.strength + self.size
        if total < 65:
            return -2
        elif total < 85:
            return -1
        elif total < 125:
            return 0
        elif total < 165:
            return 1
        else:
            return 2

    def calculate_damage_bonus(self):
        build = self.calculate_build()
        damage_bonus_map = {
            -2: "-2",
            -1: "-1",
            0: "0",
            1: "1D4",
            2: "1D6",
        }
        return damage_bonus_map.get(build, "0")

    def save(self, *args, **kwargs):
        # Auto-calculate derived values
        if not self.hp_max:
            self.hp_max = self.calculate_hp_max()
        if not self.mp_max:
            self.mp_max = self.calculate_mp_max()
        self.build = self.calculate_build()
        self.damage_bonus = self.calculate_damage_bonus()
        super().save(*args, **kwargs)

    def get_formatted_status_effects(self):
        """Get status effects formatted for UI display with badge colors"""
        effects = self.status_effects.select_related('status_effect').all()
        return [
            {
                'id': eff.status_effect.id,
                'character_effect_id': eff.id,
                'name': eff.status_effect.name,
                'effect_type': eff.status_effect.effect_type,
                'icon_class': eff.status_effect.icon_class,
                'description': eff.status_effect.description,
                'badge_color': eff.status_effect.badge_color,
            }
            for eff in effects
        ]

    def __str__(self):
        return f"{self.name} ({'Alive' if self.is_alive else 'Dead'})"

    class Meta:
        ordering = ['-created_at']


class CharacterChangeLog(models.Model):
    """Audit trail entries for character edits."""

    character = models.ForeignKey(Character, on_delete=models.CASCADE, related_name='change_logs')
    changed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='character_change_logs',
    )
    changes = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.character.name} changes @ {self.created_at:%Y-%m-%d %H:%M:%S}"


class Skill(models.Model):
    """Skills available to characters"""

    SKILL_CATEGORY_CHOICES = [
        ('mutual', _('Mutual')),
        ('general', _('General')),
        ('combat', _('Combat')),
        ('language', _('Language')),
    ]

    name = models.CharField(max_length=50, unique=True)
    category = models.CharField(max_length=10, choices=SKILL_CATEGORY_CHOICES)
    base_value = models.IntegerField(default=0)
    description = models.TextField()

    @property
    def name_uk(self):
        """Return translated skill name for Ukrainian locale"""
        return gettext(self.name)

    @property
    def description_uk(self):
        """Return translated skill description for Ukrainian locale"""
        return gettext(self.description)

    def __str__(self):
        return self.name


class CharacterSkill(models.Model):
    """Individual character's skills and their values"""

    character = models.ForeignKey(Character, on_delete=models.CASCADE, related_name='skills')
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE)
    value = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(100)])
    marked_for_improvement = models.BooleanField(default=False)
    needs_update = models.BooleanField(default=False, help_text="Keeper flag: skill needs update after session")

    class Meta:
        unique_together = ['character', 'skill']

    def __str__(self):
        return f"{self.character.name} - {self.skill.name}: {self.value}%"


class Weapon(models.Model):
    """Weapon templates"""

    name = models.CharField(max_length=50)
    skill_name = models.CharField(max_length=50)
    damage = models.CharField(max_length=20)
    attacks_per_round = models.IntegerField(default=1)
    range = models.CharField(max_length=20, blank=True)
    ammo = models.IntegerField(null=True, blank=True)
    malfunction = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return self.name


class CharacterWeapon(models.Model):
    """Weapons owned by a character"""

    character = models.ForeignKey(Character, on_delete=models.CASCADE, related_name='weapons')
    weapon = models.ForeignKey(Weapon, on_delete=models.CASCADE)
    skill_value = models.IntegerField()
    is_prepared = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.character.name} - {self.weapon.name}"


class Item(models.Model):
    """Item templates"""

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class CharacterItem(models.Model):
    """Items owned by a character"""

    character = models.ForeignKey(Character, on_delete=models.CASCADE, related_name='items')
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)

    def __str__(self):
        return f"{self.character.name} - {self.item.name} x{self.quantity}"


class Spell(models.Model):
    """Spell templates"""

    name = models.CharField(max_length=100, unique=True)
    mana_cost = models.IntegerField()
    description = models.TextField()

    def __str__(self):
        return f"{self.name} ({self.mana_cost} MP)"


class CharacterSpell(models.Model):
    """Spells known by a character"""

    character = models.ForeignKey(Character, on_delete=models.CASCADE, related_name='spells')
    spell = models.ForeignKey(Spell, on_delete=models.CASCADE)

    class Meta:
        unique_together = ['character', 'spell']

    def __str__(self):
        return f"{self.character.name} - {self.spell.name}"


class StatusEffect(models.Model):
    """Status effects that can affect characters"""

    EFFECT_TYPE_CHOICES = [
        ('NORMAL', _('Custom Status Effect')),
        ('PHOBIA', _('Phobia')),
        ('MADNESS', _('Madness')),
        ('MANIA', _('Mania')),
        ('DEEP_WOUND', _('Deep Wound')),
    ]

    BADGE_COLOR_CHOICES = [
        ('bg-warning', _('Amber')),
        ('bg-danger', _('Red')),
        ('bg-info', _('Blue')),
        ('bg-secondary', _('Gray')),
        ('bg-success', _('Green')),
        ('bg-primary', _('Indigo')),
    ]

    name = models.CharField(max_length=50, unique=True)
    description = models.TextField()
    effect_type = models.CharField(max_length=20, choices=EFFECT_TYPE_CHOICES, default='NORMAL')
    badge_color = models.CharField(max_length=20, choices=BADGE_COLOR_CHOICES, default='bg-warning')
    is_permanent = models.BooleanField(default=False, help_text="If true, effect cannot be automatically removed")
    icon_class = models.CharField(max_length=50, default='bi-shield-exclamation', help_text="Bootstrap icon class for display")
    game_rules_json = models.JSONField(default=dict, blank=True, help_text="Custom game rules data")

    class Meta:
        ordering = ['effect_type', 'name']

    def __str__(self):
        return f"{self.name} ({self.get_effect_type_display()})"


class CharacterStatusEffect(models.Model):
    """Active status effects on a character"""

    character = models.ForeignKey(Character, on_delete=models.CASCADE, related_name='status_effects')
    status_effect = models.ForeignKey(StatusEffect, on_delete=models.CASCADE)
    remaining_rounds = models.IntegerField()
    acquired_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-acquired_at']

    def __str__(self):
        return f"{self.character.name} - {self.status_effect.name} ({self.remaining_rounds} rounds)"


class MentalDisorder(models.Model):
    """Mental disorders that can affect characters"""

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField()

    def __str__(self):
        return self.name


class CharacterMentalDisorder(models.Model):
    """Mental disorders affecting a character"""

    character = models.ForeignKey(Character, on_delete=models.CASCADE, related_name='mental_disorders')
    disorder = models.ForeignKey(MentalDisorder, on_delete=models.CASCADE)

    class Meta:
        unique_together = ['character', 'disorder']

    def __str__(self):
        return f"{self.character.name} - {self.disorder.name}"


class CharacterTemplate(models.Model):
    """Keeper-managed character templates persisted in the database."""

    name = models.CharField(max_length=150)
    payload = models.JSONField(default=dict)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_character_templates',
    )
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='updated_character_templates',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name', 'id']

    def __str__(self):
        return self.name


class NPCTemplate(models.Model):
    """Keeper-managed NPC templates persisted in the database."""

    name = models.CharField(max_length=150)
    payload = models.JSONField(default=dict)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_npc_templates',
    )
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='updated_npc_templates',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name', 'id']

    def __str__(self):
        return self.name

