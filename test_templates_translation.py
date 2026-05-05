#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cthulhu_rpg.settings')
django.setup()

from django.utils.translation import activate
activate('uk')

from characters.views import _load_character_templates, _load_npc_templates

print("✓ Testing template loading with translations...")
print()

# Load character templates
char_templates = _load_character_templates()
if char_templates:
    print(f"Character Templates Found: {len(char_templates)}")
    template = char_templates[0]
    print(f"  Template Name: {template['name']}")
    print(f"  Stats: STR={template['STR']}, CON={template['CON']}, DEX={template['DEX']}")
    if template.get('top_skills'):
        print(f"  Top Skills (translated):")
        for skill_name, skill_val in template['top_skills'][:3]:
            print(f"    - {skill_name}: {skill_val}%")
else:
    print("⚠ No character templates found")

print()

# Load NPC templates
npc_templates = _load_npc_templates()
if npc_templates:
    print(f"NPC Templates Found: {len(npc_templates)}")
    template = npc_templates[0]
    print(f"  Template Name: {template['name']}")
    print(f"  Stats: STR={template['STR']}, CON={template['CON']}, DEX={template['DEX']}")
    if template.get('top_skills'):
        print(f"  Top Skills (translated):")
        for skill_name, skill_val in template['top_skills'][:3]:
            print(f"    - {skill_name}: {skill_val}%")
else:
    print("⚠ No NPC templates found")

print()
print("✓ All template translation tests completed!")

