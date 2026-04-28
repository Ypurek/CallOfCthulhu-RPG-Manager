"""Game logic services for Cthulhu RPG scenarios"""

from characters.models import Character, StatusEffect, CharacterStatusEffect
from scenarios.models import Scenario, ScenarioPlayer, ScenarioNPC


def _get_scenario_character_ids(scenario: Scenario):
    """Return all unique PC/NPC character IDs participating in the scenario."""
    character_ids = set()

    for sp in ScenarioPlayer.objects.filter(scenario=scenario).select_related('character'):
        if sp.character:
            character_ids.add(sp.character.id)

    for snpc in ScenarioNPC.objects.filter(scenario=scenario).select_related('npc'):
        if snpc.npc:
            character_ids.add(snpc.npc.id)

    return character_ids


def apply_daily_hp_restore(scenario: Scenario, days: int = 1):
    """
    Apply daily HP restoration for characters without deep wound.
    Called when in_game_day is incremented.

    If multiple in-game days pass at once, restore 1 HP per day crossed.
    """
    if days <= 0:
        return

    deep_wound = StatusEffect.objects.filter(name='Deep Wound').first()

    character_ids = _get_scenario_character_ids(scenario)

    # Apply restoration
    for char_id in character_ids:
        try:
            character = Character.objects.get(id=char_id)

            # Skip if character has deep wound
            if deep_wound and CharacterStatusEffect.objects.filter(
                character=character,
                status_effect=deep_wound
            ).exists():
                continue

            # Restore 1 HP per day crossed (up to max)
            if character.hp_current < character.hp_max:
                character.hp_current = min(character.hp_current + days, character.hp_max)
                character.save(update_fields=['hp_current'])
        except Character.DoesNotExist:
            continue


def apply_hourly_mp_restore(scenario: Scenario, hours: int = 1):
    """Restore 1 MP per in-game hour crossed (up to max MP)."""
    if hours <= 0:
        return

    character_ids = _get_scenario_character_ids(scenario)

    for char_id in character_ids:
        try:
            character = Character.objects.get(id=char_id)
            if character.mp_current < character.mp_max:
                character.mp_current = min(character.mp_current + hours, character.mp_max)
                character.save(update_fields=['mp_current'])
        except Character.DoesNotExist:
            continue


def apply_near_death_status(character: Character):
    """
    Add 'Near Death' status when character reaches 0 HP.
    Notifies the player to roll CON each turn to avoid death.
    """
    if character.hp_current != 0:
        return

    try:
        near_death = StatusEffect.objects.get(name='Near Death')
    except StatusEffect.DoesNotExist:
        return

    # Check if already has status
    if CharacterStatusEffect.objects.filter(
        character=character,
        status_effect=near_death
    ).exists():
        return

    # Add status (infinite rounds = permanent until healed)
    CharacterStatusEffect.objects.create(
        character=character,
        status_effect=near_death,
        remaining_rounds=999999  # Permanent until HP > 0
    )


def apply_trauma_status(character: Character, sanity_lost: int):
    """
    Add 'Psychological Trauma' status when character loses 5+ SAN at once.
    """
    if sanity_lost < 5:
        return

    try:
        trauma = StatusEffect.objects.get(name='Psychological Trauma')
    except StatusEffect.DoesNotExist:
        return

    # Check if already has status
    if CharacterStatusEffect.objects.filter(
        character=character,
        status_effect=trauma
    ).exists():
        return

    # Add status (temporary)
    CharacterStatusEffect.objects.create(
        character=character,
        status_effect=trauma,
        remaining_rounds=10  # 10 rounds to resolve
    )


def apply_deep_wound_from_damage(character: Character, damage_taken: int):
    """
    Automatically add 'Deep Wound' status if damage is 50% or more of max HP in one hit.
    """
    if character.hp_max == 0:
        return

    damage_threshold = character.hp_max * 0.5
    if damage_taken < damage_threshold:
        return

    try:
        deep_wound = StatusEffect.objects.get(name='Deep Wound')
    except StatusEffect.DoesNotExist:
        return

    # Check if already has status
    if CharacterStatusEffect.objects.filter(
        character=character,
        status_effect=deep_wound
    ).exists():
        return

    # Add status (permanent until manually removed)
    CharacterStatusEffect.objects.create(
        character=character,
        status_effect=deep_wound,
        remaining_rounds=999999
    )


def remove_status_effect(character: Character, status_effect: StatusEffect):
    """
    Manually remove a status effect from a character.
    """
    CharacterStatusEffect.objects.filter(
        character=character,
        status_effect=status_effect
    ).delete()


def add_status_effect(character: Character, status_effect: StatusEffect, remaining_rounds: int = 1):
    """
    Manually add a status effect to a character.
    If permanent, use a large number for remaining_rounds.
    """
    # Check if already exists
    existing = CharacterStatusEffect.objects.filter(
        character=character,
        status_effect=status_effect
    ).first()

    if existing:
        # Update remaining rounds if adding another instance
        return existing

    return CharacterStatusEffect.objects.create(
        character=character,
        status_effect=status_effect,
        remaining_rounds=remaining_rounds
    )


def get_character_status_effects_display(character: Character):
    """
    Get formatted display of all character status effects for UI badge display.
    """
    effects = character.status_effects.select_related('status_effect').all()
    return [
        {
            'id': eff.status_effect.id,
            'character_effect_id': eff.id,
            'name': eff.status_effect.name,
            'effect_type': eff.status_effect.effect_type,
            'icon_class': eff.status_effect.icon_class,
            'description': eff.status_effect.description,
            'badge_color': _get_badge_color_for_effect_type(eff.status_effect.effect_type),
        }
        for eff in effects
    ]


def _get_badge_color_for_effect_type(effect_type: str) -> str:
    """Map effect type to Bootstrap badge color classes"""
    color_map = {
        'NORMAL': 'bg-warning',
        'PHOBIA': 'bg-danger',
        'MADNESS': 'bg-dark',
        'MANIA': 'bg-info',
        'DEEP_WOUND': 'bg-danger',
    }
    return color_map.get(effect_type, 'bg-secondary')

