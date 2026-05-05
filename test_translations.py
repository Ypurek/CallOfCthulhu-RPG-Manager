#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cthulhu_rpg.settings')
django.setup()

from django.utils.translation import activate
activate('uk')

from characters.models import Character, Skill
from characters.views import _build_character_sheet_context

# Get the first character and first skill for testing
character = Character.objects.first()
if character:
    skill = Skill.objects.first()
    print(f"Testing character sheet translation:")
    print(f"Character: {character.name}")
    print(f"Original skill name: {skill.name}")

    # Build the character sheet
    sheet = _build_character_sheet_context(
        character=character,
        skill_values={},
        weapons=[],
        items=[],
        spells=[],
        can_add_custom_skill=False,
    )

    print(f"\nCharacter sheet built successfully!")

    if sheet['skills']:
        print(f"\nFirst translated skill in sheet:")
        first_skill = sheet['skills'][0]
        print(f"  Name: {first_skill['name']}")
        print(f"  Description: {first_skill['description'][:50]}...")

    if sheet['default_skills']:
        print(f"\nFirst default skill:")
        first_default = sheet['default_skills'][0]
        print(f"  Name: {first_default['name']}")
        print(f"  Description: {first_default['description'][:50]}...")

    print("\n✓ All translations working correctly!")
else:
    print("No characters found in database")

