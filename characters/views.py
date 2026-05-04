import json
import re
from urllib.parse import urlencode

from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db import DatabaseError
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext
from .models import (
    Character,
    CharacterChangeLog,
    CharacterItem,
    CharacterSkill,
    CharacterTemplate,
    CharacterWeapon,
    Item,
    NPCTemplate,
    Skill,
    Weapon,
)

WIZARD_SESSION_KEY = 'character_create_draft'
WIZARD_STEPS = ['basic', 'stats', 'skills', 'inventory', 'review']
DEFAULT_UNARMED_WEAPON_NAME = 'Unarmed Brawl'
DEFAULT_UNARMED_WEAPON_DAMAGE = '1D3 + DB'
NON_EDITABLE_SKILL_NAMES = ['Cthulhu Mythos', 'Own Language', 'English', 'Dodge']
CUSTOM_SKILL_DESCRIPTION_PREFIXES = ('Custom skill:', 'Imported custom skill:')

# NPC wizard constants
NPC_WIZARD_SESSION_KEY = 'npc_create_draft'
NPC_WIZARD_STEPS = ['basic', 'stats', 'skills', 'inventory', 'review']
NPC_TEMPLATE_WIZARD_META_KEY = 'npc_template_wizard_meta'
NPC_WIZARD_TARGET_SCENARIO = 'npc_wizard_target_scenario'


def _to_int(value, default=0, minimum=None, maximum=None):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    if minimum is not None:
        parsed = max(minimum, parsed)
    if maximum is not None:
        parsed = min(maximum, parsed)
    return parsed


def _default_stats():
    return {
        'strength': 0,
        'constitution': 0,
        'dexterity': 0,
        'intelligence': 0,
        'power': 0,
        'size': 0,
        'appearance': 0,
        'education': 0,
        'luck': 0,
    }


def _initialize_skill_values(education, existing=None):
    skill_values = {} if existing is None else {str(key): int(value) for key, value in existing.items()}
    for skill in Skill.objects.all():
        if _is_custom_skill_record(skill):
            continue
        key = str(skill.id)
        if key not in skill_values:
            skill_values[key] = skill.base_value
        if skill.name in {'Own Language', 'English'}:
            skill_values[key] = education
        if skill.name == 'Cthulhu Mythos':
            skill_values[key] = 0
    return skill_values


def _default_custom_skills():
    return {}


def _is_custom_skill_record(skill):
    return str(skill.description or '').startswith(CUSTOM_SKILL_DESCRIPTION_PREFIXES)


def _built_in_skill_queryset():
    return Skill.objects.exclude(name__in=NON_EDITABLE_SKILL_NAMES).exclude(
        description__startswith=CUSTOM_SKILL_DESCRIPTION_PREFIXES[0]
    ).exclude(
        description__startswith=CUSTOM_SKILL_DESCRIPTION_PREFIXES[1]
    )


def _normalize_custom_skill_category(category, default='general'):
    allowed_categories = {'mutual', 'general', 'combat', 'language'}
    return category if category in allowed_categories else default


def _normalize_custom_skill_key(raw_key):
    key = str(raw_key).strip()
    if not key:
        return None
    try:
        parsed = int(key)
    except (TypeError, ValueError):
        return None
    return str(parsed) if parsed < 0 else None


def _normalize_custom_skills(entries):
    if not isinstance(entries, dict):
        return {}

    normalized = {}
    for raw_key, payload in entries.items():
        key = _normalize_custom_skill_key(raw_key)
        if not key or not isinstance(payload, dict):
            continue
        name = str(payload.get('name', '')).strip()
        if not name:
            continue
        normalized[key] = {
            'name': name,
            'category': _normalize_custom_skill_category(payload.get('category'), 'general'),
            'base_value': _to_int(payload.get('base_value'), 1, 1, 100),
            'description': str(payload.get('description') or f'Custom skill: {name}').strip(),
        }
    return normalized


def _sync_custom_skill_values(draft):
    draft['custom_skills'] = _normalize_custom_skills(draft.get('custom_skills', {}))
    draft.setdefault('skills', {})

    custom_skill_keys = set(draft['custom_skills'].keys())
    for custom_skill_key, payload in draft['custom_skills'].items():
        draft['skills'].setdefault(custom_skill_key, payload.get('base_value', 1))

    for skill_key in list(draft['skills'].keys()):
        normalized_key = _normalize_custom_skill_key(skill_key)
        if normalized_key and normalized_key not in custom_skill_keys:
            draft['skills'].pop(skill_key, None)

    return draft


def _next_custom_skill_key(existing_custom_skills):
    negative_ids = [int(key) for key in _normalize_custom_skills(existing_custom_skills).keys()]
    return str(min(negative_ids, default=0) - 1)


def _infer_custom_skill_category(raw_name):
    raw_name = str(raw_name or '')
    if raw_name.startswith('Language_'):
        return 'language'
    if raw_name.startswith('Fighting_') or raw_name.startswith('Firearms_'):
        return 'combat'
    return 'general'


def _build_skill_options_from_draft(draft):
    skill_options = [
        {
            'id': skill.id,
            'name': gettext(skill.name),
            'category': skill.category,
            'value': draft['skills'].get(str(skill.id), skill.base_value),
            'base_value': skill.base_value,
            'is_custom': False,
        }
        for skill in _built_in_skill_queryset().order_by('category', 'name')
    ]

    for custom_skill_id, payload in sorted(
        draft.get('custom_skills', {}).items(),
        key=lambda item: (item[1].get('category', 'general'), item[1].get('name', '').lower()),
    ):
        skill_options.append({
            'id': custom_skill_id,
            'name': payload['name'],
            'category': payload['category'],
            'value': draft['skills'].get(custom_skill_id, payload.get('base_value', 1)),
            'base_value': payload.get('base_value', 1),
            'is_custom': True,
        })

    return skill_options


def _build_combat_skill_options_from_draft(draft):
    return [
        {
            'id': skill_option['id'],
            'name': skill_option['name'],
            'value': skill_option['value'],
        }
        for skill_option in _build_skill_options_from_draft(draft)
        if skill_option['category'] == 'combat'
    ]


def _materialize_custom_skills(draft):
    custom_skill_id_map = {}
    for custom_skill_id, payload in _normalize_custom_skills(draft.get('custom_skills', {})).items():
        skill, _ = Skill.objects.get_or_create(
            name=payload['name'],
            defaults={
                'category': payload['category'],
                'base_value': payload.get('base_value', 1),
                'description': payload.get('description') or f"Custom skill: {payload['name']}",
            },
        )
        custom_skill_id_map[custom_skill_id] = skill.id
    return custom_skill_id_map


def _resolve_skill_values_for_storage(draft, education):
    custom_skill_id_map = _materialize_custom_skills(draft)
    resolved_skill_values = {}

    for raw_skill_id, value in draft.get('skills', {}).items():
        skill_key = str(raw_skill_id)
        if skill_key in custom_skill_id_map:
            resolved_skill_values[str(custom_skill_id_map[skill_key])] = _to_int(value, 1, 0, 100)
            continue

        parsed_skill_id = _to_int(skill_key, None)
        if parsed_skill_id and parsed_skill_id > 0:
            skill = Skill.objects.filter(id=parsed_skill_id).first()
            if skill and skill.name == 'Dodge':
                continue
            resolved_skill_values[str(parsed_skill_id)] = _to_int(value, 0, 0, 100)

    return _initialize_skill_values(education, resolved_skill_values), custom_skill_id_map


def _derive_secondary_stats(stats, cthulhu_mythos=0):
    hp_max = max((_to_int(stats.get('strength')) + _to_int(stats.get('constitution'))) // 10, 1)
    mp_max = max(_to_int(stats.get('power')) // 5, 1)
    sanity_max = max(99 - _to_int(cthulhu_mythos, 0, 0, 99), 0)
    sanity_current = min(_to_int(stats.get('power')), sanity_max)
    return {
        'hp_max': hp_max,
        'hp_current': hp_max,
        'mp_max': mp_max,
        'mp_current': mp_max,
        'sanity_start': sanity_current,
        'sanity_max': sanity_max,
        'sanity_current': sanity_current,
    }


def _get_default_combat_skill():
    return (
        Skill.objects.filter(name='Fighting (Brawl)').first()
        or Skill.objects.filter(category='combat').order_by('name').first()
    )


def _ensure_default_unarmed_weapon_entry(draft):
    inventory = draft.setdefault('inventory', {'weapons': [], 'items': []})
    weapons = inventory.setdefault('weapons', [])

    default_skill = _get_default_combat_skill()
    default_entry = {
        'weapon_id': 0,
        'custom_name': DEFAULT_UNARMED_WEAPON_NAME,
        'name': DEFAULT_UNARMED_WEAPON_NAME,
        'damage': DEFAULT_UNARMED_WEAPON_DAMAGE,
        'skill_id': default_skill.id if default_skill else 0,
        'skill_name': default_skill.name if default_skill else 'Fighting (Brawl)',
        'is_prepared': False,
        'is_default_unarmed': True,
    }

    existing_entries = [weapon for weapon in weapons if weapon.get('is_default_unarmed')]
    if existing_entries:
        entry = existing_entries[0]
        entry.update(default_entry)
        inventory['weapons'] = [entry] + [weapon for weapon in weapons if weapon is not entry and not weapon.get('is_default_unarmed')]
    else:
        inventory['weapons'] = [default_entry] + weapons

    return draft


def _default_draft():
    stats = _default_stats()
    draft = {
        'step': 'basic',
        'basic': {
            'name': '',
            'description': '',
            'occupation': '',
            'age': '',
        },
        'stats': stats,
        'skills': _initialize_skill_values(stats['education']),
        'custom_skills': _default_custom_skills(),
        'inventory': {
            'weapons': [],
            'items': [],
        },
    }
    return _sync_custom_skill_values(_ensure_default_unarmed_weapon_entry(draft))


def _get_draft(request):
    draft = request.session.get(WIZARD_SESSION_KEY)
    if not draft:
        draft = _default_draft()
    draft.setdefault('basic', _default_draft()['basic'])
    draft.setdefault('stats', _default_stats())
    draft['skills'] = _initialize_skill_values(draft['stats'].get('education', 0), draft.get('skills', {}))
    draft.setdefault('custom_skills', _default_custom_skills())
    draft.setdefault('inventory', {'weapons': [], 'items': []})
    draft['inventory'].setdefault('weapons', [])
    draft['inventory'].setdefault('items', [])
    if not isinstance(draft['inventory']['weapons'], list):
        draft['inventory']['weapons'] = []
    if not isinstance(draft['inventory']['items'], list):
        draft['inventory']['items'] = []
    return _sync_custom_skill_values(_ensure_default_unarmed_weapon_entry(draft))


def _save_draft(request, draft):
    request.session[WIZARD_SESSION_KEY] = draft
    request.session.modified = True


def _export_payload_from_draft(draft):
    basic = draft['basic']
    draft = _sync_custom_skill_values(draft)
    skills_by_id = {str(skill.id): skill for skill in Skill.objects.all()}
    exported_skills = {}
    for skill_id, value in draft.get('skills', {}).items():
        skill_key = str(skill_id)
        skill = skills_by_id.get(skill_key)
        if skill:
            exported_skills[_skill_name_to_export_key(skill.name, skill.category)] = _to_int(value, skill.base_value, 0, 100)
            continue
        custom_skill = draft.get('custom_skills', {}).get(skill_key)
        if custom_skill:
            exported_skills[_skill_name_to_export_key(custom_skill['name'], custom_skill['category'])] = _to_int(
                value,
                custom_skill.get('base_value', 1),
                0,
                100,
            )
    return {
        'version': 1,
        'character_info': {
            'name': basic.get('name', ''),
            'occupation': basic.get('occupation', ''),
            'age': basic.get('age', ''),
        },
        'description': basic.get('description', ''),
        'characteristics': {
            'STR': draft['stats'].get('strength', 0),
            'CON': draft['stats'].get('constitution', 0),
            'DEX': draft['stats'].get('dexterity', 0),
            'INT': draft['stats'].get('intelligence', 0),
            'APP': draft['stats'].get('appearance', 0),
            'POW': draft['stats'].get('power', 0),
            'SIZ': draft['stats'].get('size', 0),
            'EDU': draft['stats'].get('education', 0),
            'Luck': draft['stats'].get('luck', 0),
        },
        'skills': exported_skills,
        'weapons': [
            {
                'name': w.get('name') or w.get('custom_name', ''),
                'damage': w.get('damage', ''),
                'is_prepared': w.get('is_prepared', False),
            }
            for w in draft.get('inventory', {}).get('weapons', [])
            if not w.get('is_default_unarmed')
        ],
        'inventory': [
            '{}{}'.format(
                item.get('name') or item.get('custom_name', ''),
                ' x{}'.format(item['quantity']) if item.get('quantity', 1) > 1 else ''
            )
            for item in draft.get('inventory', {}).get('items', [])
        ],
    }


def _normalize_imported_skill_name(raw_name):
    mapping = {
        'Fighting_Brawl': 'Fighting (Brawl)',
        'Firearms_Rifle_Shotgun': 'Firearms (Rifle/Shotgun)',
        'Firearms_Handgun': 'Firearms (Handgun)',
        'Firearms_Bow_Crossbow': 'Firearms (Bow/Crossbow)',
        'Language_English_Own': 'Own Language',
        'Language_Italian': 'Foreign Language',
        'Repair_Electrical': 'Repair (Electrical)',
        'Repair_Mechanical': 'Repair (Mechanical)',
    }
    if raw_name in mapping:
        return mapping[raw_name]
    if str(raw_name).startswith('Language_'):
        return str(raw_name).replace('Language_', '', 1).replace('_', ' ').strip()
    return raw_name.replace('_', ' ').strip()


def _normalize_imported_custom_skill_name(raw_name):
    normalized_name = _normalize_imported_skill_name(raw_name)
    if str(raw_name).startswith('Language_') and normalized_name.startswith('Language '):
        return normalized_name[len('Language '):].strip()
    return normalized_name


def _draft_from_import(data):
    draft = _default_draft()
    if 'basic' in data and 'stats' in data:
        draft['basic'].update(data.get('basic', {}))
        draft['stats'].update(data.get('stats', {}))
        draft['skills'] = _initialize_skill_values(draft['stats'].get('education', 0), data.get('skills', {}))
        draft['inventory'] = data.get('inventory', draft['inventory'])
        draft['inventory'].setdefault('weapons', [])
        draft['inventory'].setdefault('items', [])
        if not isinstance(draft['inventory']['weapons'], list):
            draft['inventory']['weapons'] = []
        if not isinstance(draft['inventory']['items'], list):
            draft['inventory']['items'] = []
        return _sync_custom_skill_values(_ensure_default_unarmed_weapon_entry(draft))

    # Support importing sheet-shaped JSON like docs/characters/*.json.
    info = data.get('character_info', {})
    # Prefer top-level 'description'; fall back to assembling from legacy 'backstory' subfields.
    backstory = data.get('backstory', {})
    if data.get('description'):
        description = data['description']
    elif backstory:
        parts = []
        for field in ['appearance', 'ideology_beliefs', 'significant_people', 'meaningful_locations', 'treasured_possessions', 'traits']:
            value = backstory.get(field, '').strip()
            if value and value != 'Н/Д':
                parts.append(value)
        description = ' '.join(parts)
    else:
        description = ''
    draft['basic'].update({
        'name': info.get('name', ''),
        'description': description,
        'occupation': info.get('occupation', ''),
        'age': info.get('age', ''),
    })

    characteristics = data.get('characteristics', {})
    status = data.get('status', {})
    draft['stats'].update({
        'strength': _to_int(characteristics.get('STR', 0), 0, 0, 100),
        'constitution': _to_int(characteristics.get('CON', 0), 0, 0, 100),
        'dexterity': _to_int(characteristics.get('DEX', 0), 0, 0, 100),
        'intelligence': _to_int(characteristics.get('INT', 0), 0, 0, 100),
        'power': _to_int(characteristics.get('POW', 0), 0, 0, 100),
        'size': _to_int(characteristics.get('SIZ', 0), 0, 0, 100),
        'appearance': _to_int(characteristics.get('APP', 0), 0, 0, 100),
        'education': _to_int(characteristics.get('EDU', 0), 0, 0, 100),
        'luck': _to_int(characteristics.get('Luck', 0), 0, 0, 100),
    })

    # Preserve optional status values (HP/MP/SAN/LCK) for wizards that support bar adjustments.
    derived_stats = _derive_secondary_stats(draft['stats'], 0)
    status_payload = data.get('status', {}) if isinstance(data.get('status'), dict) else {}
    hp_payload = status_payload.get('HP', {}) if isinstance(status_payload.get('HP'), dict) else {}
    mp_payload = status_payload.get('MP', {}) if isinstance(status_payload.get('MP'), dict) else {}
    sanity_payload = status_payload.get('Sanity', {}) if isinstance(status_payload.get('Sanity'), dict) else {}
    draft['adjustments'] = {
        'hp': _to_int(hp_payload.get('current'), derived_stats['hp_current'], 0) - derived_stats['hp_current'],
        'mp': _to_int(mp_payload.get('current'), derived_stats['mp_current'], 0) - derived_stats['mp_current'],
        'sanity': _to_int(sanity_payload.get('current'), derived_stats['sanity_current'], 0) - derived_stats['sanity_current'],
        'luck': 0,
    }

    imported_skills = {}
    custom_skills = {}
    skills_by_name = {skill.name.lower(): skill for skill in Skill.objects.all() if not _is_custom_skill_record(skill)}
    skills_by_id = {skill.id: skill for skill in Skill.objects.all()}
    for raw_name, value in data.get('skills', {}).items():
        # Handle both ID-based keys (exported by this app) and name-based keys (template files).
        if str(raw_name).isdigit():
            skill = skills_by_id.get(int(raw_name))
        else:
            normalized_name = _normalize_imported_skill_name(raw_name)
            skill = skills_by_name.get(normalized_name.lower())
        if skill:
            imported_skills[str(skill.id)] = _to_int(value, skill.base_value, 0, 100)
        else:
            custom_skill_key = _next_custom_skill_key(custom_skills)
            custom_skill_name = _normalize_imported_custom_skill_name(raw_name)
            custom_skills[custom_skill_key] = {
                'name': custom_skill_name,
                'category': _infer_custom_skill_category(raw_name),
                'base_value': 1,
                'description': f'Imported custom skill: {custom_skill_name}',
            }
            imported_skills[custom_skill_key] = _to_int(value, 1, 0, 100)
    draft['custom_skills'] = custom_skills
    draft['skills'] = _initialize_skill_values(draft['stats']['education'], imported_skills)

    inventory = draft['inventory']
    weapons_by_name = {weapon.name.lower(): weapon for weapon in Weapon.objects.all()}
    items_by_name = {item.name.lower(): item for item in Item.objects.all()}
    for weapon_payload in data.get('weapons', []):
        weapon = weapons_by_name.get(str(weapon_payload.get('name', '')).lower())
        if weapon:
            selected_skill = Skill.objects.filter(name__iexact=weapon.skill_name).first() or _get_default_combat_skill()
            inventory['weapons'].append({
                'weapon_id': weapon.id,
                'name': weapon.name,
                'skill_id': selected_skill.id if selected_skill else 0,
                'skill_name': selected_skill.name if selected_skill else weapon.skill_name,
                'is_prepared': bool(weapon_payload.get('is_prepared', False)),
                'damage': weapon.damage,
            })
        elif weapon_payload.get('name'):
            selected_skill = _get_default_combat_skill()
            inventory['weapons'].append({
                'custom_name': str(weapon_payload.get('name')).strip(),
                'name': str(weapon_payload.get('name')).strip(),
                'damage': str(weapon_payload.get('damage') or '1D4').strip(),
                'skill_id': selected_skill.id if selected_skill else 0,
                'skill_name': selected_skill.name if selected_skill else 'Fighting (Brawl)',
                'is_prepared': bool(weapon_payload.get('is_prepared', False)),
            })
    for item_entry in data.get('inventory', []):
        # Inventory entries may be plain strings (template format) or dicts (export format).
        if isinstance(item_entry, dict):
            raw_name = str(item_entry.get('name') or item_entry.get('custom_name') or '').strip()
            qty = _to_int(item_entry.get('quantity'), 1, 1)
        else:
            raw_name = str(item_entry).strip()
            qty = 1
        if not raw_name:
            continue
        # Strip trailing " xN" quantity suffix that _export_payload_from_draft adds.
        match = re.match(r'^(.+?)\s+x(\d+)$', raw_name)
        if match:
            raw_name = match.group(1).strip()
            qty = int(match.group(2))
        item = items_by_name.get(raw_name.lower())
        if item:
            inventory['items'].append({'item_id': item.id, 'name': item.name, 'custom_name': item.name, 'quantity': qty})
        else:
            inventory['items'].append({'item_id': 0, 'custom_name': raw_name, 'name': raw_name, 'quantity': qty})

    return _sync_custom_skill_values(_ensure_default_unarmed_weapon_entry(draft))


def _create_character_from_draft(user, draft):
    stats = draft['stats']
    basic = draft['basic']

    base_stats = {
        'strength': _to_int(stats.get('strength'), 0, 0, 100),
        'constitution': _to_int(stats.get('constitution'), 0, 0, 100),
        'dexterity': _to_int(stats.get('dexterity'), 0, 0, 100),
        'intelligence': _to_int(stats.get('intelligence'), 0, 0, 100),
        'power': _to_int(stats.get('power'), 0, 0, 100),
        'size': _to_int(stats.get('size'), 0, 0, 100),
        'appearance': _to_int(stats.get('appearance'), 0, 0, 100),
        'education': _to_int(stats.get('education'), 0, 0, 100),
        'luck': _to_int(stats.get('luck'), 0, 0, 100),
    }

    skill_values, custom_skill_id_map = _resolve_skill_values_for_storage(draft, base_stats['education'])
    cthulhu_mythos = 0
    for skill in Skill.objects.filter(name='Cthulhu Mythos'):
        cthulhu_mythos = _to_int(skill_values.get(str(skill.id), 0), 0, 0, 99)
        break

    derived_stats = _derive_secondary_stats(base_stats, cthulhu_mythos)

    character = Character.objects.create(
        owner=user,
        character_type='PC',
        is_alive=True,
        name=basic.get('name') or 'Unnamed Character',
        description=basic.get('description', ''),
        birthplace='',
        residence='',
        occupation=basic.get('occupation', ''),
        gender='',
        age=_to_int(basic.get('age'), None) if str(basic.get('age', '')).strip() else None,
        strength=base_stats['strength'],
        constitution=base_stats['constitution'],
        dexterity=base_stats['dexterity'],
        intelligence=base_stats['intelligence'],
        power=base_stats['power'],
        size=base_stats['size'],
        appearance=base_stats['appearance'],
        education=base_stats['education'],
        hp_current=derived_stats['hp_current'],
        hp_max=derived_stats['hp_max'],
        mp_current=derived_stats['mp_current'],
        mp_max=derived_stats['mp_max'],
        sanity_current=derived_stats['sanity_current'],
        sanity_max=derived_stats['sanity_max'],
        sanity_start=derived_stats['sanity_start'],
        luck=base_stats['luck'],
        movement=0,
        build=0,
        damage_bonus='0',
        cash=_to_int(draft.get('inventory', {}).get('cash'), 0, 0),
    )

    skill_values, custom_skill_id_map = _resolve_skill_values_for_storage(draft, character.education)
    skills_by_id = {skill.id: skill for skill in Skill.objects.all()}
    CharacterSkill.objects.bulk_create([
        CharacterSkill(
            character=character,
            skill=skills_by_id[skill_id],
            value=_to_int(value, skills_by_id[skill_id].base_value, 0, 100),
        )
        for skill_id_str, value in skill_values.items()
        if (skill_id := _to_int(skill_id_str, None)) in skills_by_id
    ])

    inventory = draft.get('inventory', {})
    for payload in inventory.get('weapons', []):
        weapon = None
        selected_skill_id = str(payload.get('skill_id', ''))
        if selected_skill_id in custom_skill_id_map:
            selected_skill = Skill.objects.filter(id=custom_skill_id_map[selected_skill_id]).first()
        else:
            selected_skill = Skill.objects.filter(id=_to_int(payload.get('skill_id'), -1)).first()
        selected_skill_name = selected_skill.name if selected_skill else str(payload.get('skill_name') or 'Custom').strip()
        selected_skill_value = skill_values.get(str(selected_skill.id), 0) if selected_skill else 0
        if payload.get('weapon_id'):
            weapon = Weapon.objects.filter(id=_to_int(payload.get('weapon_id'), -1)).first()
        custom_name = str(payload.get('custom_name', '')).strip()
        if not weapon and custom_name:
            weapon = Weapon.objects.filter(name__iexact=custom_name, skill_name=selected_skill_name).first()
            if not weapon:
                weapon = Weapon.objects.create(
                    name=custom_name,
                    skill_name=selected_skill_name,
                    damage=str(payload.get('damage') or '1D4').strip() or '1D4',
                )
        elif weapon and selected_skill_name and weapon.skill_name != selected_skill_name:
            weapon = (
                Weapon.objects.filter(
                    name=weapon.name,
                    skill_name=selected_skill_name,
                    damage=weapon.damage,
                    attacks_per_round=weapon.attacks_per_round,
                    range=weapon.range,
                    ammo=weapon.ammo,
                    malfunction=weapon.malfunction,
                ).first()
                or Weapon.objects.create(
                    name=weapon.name,
                    skill_name=selected_skill_name,
                    damage=weapon.damage,
                    attacks_per_round=weapon.attacks_per_round,
                    range=weapon.range,
                    ammo=weapon.ammo,
                    malfunction=weapon.malfunction,
                )
            )
        if weapon:
            CharacterWeapon.objects.create(
                character=character,
                weapon=weapon,
                skill_value=selected_skill_value,
                is_prepared=bool(payload.get('is_prepared', False)),
            )

    for payload in inventory.get('items', []):
        parsed_quantity = _to_int(payload.get('quantity'), 0, 0)
        if parsed_quantity <= 0:
            continue
        item = None
        if payload.get('item_id'):
            item = Item.objects.filter(id=_to_int(payload.get('item_id'), -1)).first()
        custom_name = str(payload.get('custom_name', '')).strip()
        if not item and custom_name:
            item, _ = Item.objects.get_or_create(name=custom_name, defaults={'description': ''})
        if item:
            CharacterItem.objects.create(character=character, item=item, quantity=parsed_quantity)

    return character


def _normalize_preview_weapons(weapon_entries):
    normalized = []
    for entry in weapon_entries or []:
        if not isinstance(entry, dict):
            continue
        name = entry.get('name') or entry.get('custom_name') or DEFAULT_UNARMED_WEAPON_NAME
        normalized.append({
            'name': name,
            'damage': entry.get('damage') or DEFAULT_UNARMED_WEAPON_DAMAGE,
            'is_prepared': bool(entry.get('is_prepared', False)),
        })
    return normalized


def _normalize_preview_items(item_entries):
    normalized = []
    item_names = {item.id: item.name for item in Item.objects.all()}
    for entry in item_entries or []:
        if not isinstance(entry, dict):
            continue
        item_id = _to_int(entry.get('item_id'), 0)
        name = entry.get('name') or entry.get('custom_name') or item_names.get(item_id, '')
        quantity = _to_int(entry.get('quantity'), 0, 0)
        if name and quantity > 0:
            normalized.append({'name': name, 'quantity': quantity})
    return normalized


def _build_character_sheet_context(character, skill_values=None, weapons=None, items=None, spells=None, can_add_custom_skill=False, custom_skills=None, needs_update_skill_ids=None):
    education = getattr(character, 'education', 0)
    dexterity = getattr(character, 'dexterity', 0)
    skill_values = {} if skill_values is None else {int(key): int(value) for key, value in skill_values.items()}
    needs_update_skill_ids = set(needs_update_skill_ids or [])
    custom_skills = _normalize_custom_skills(custom_skills or {})
    persisted_custom_skills = {}
    if isinstance(character, Character) and getattr(character, 'id', None):
        for char_skill in CharacterSkill.objects.filter(character=character).select_related('skill'):
            if _is_custom_skill_record(char_skill.skill):
                persisted_custom_skills[str(char_skill.skill_id)] = {
                    'name': char_skill.skill.name,
                    'category': char_skill.skill.category,
                    'base_value': char_skill.skill.base_value,
                    'description': char_skill.skill.description,
                }
    merged_custom_skills = {**persisted_custom_skills, **custom_skills}

    def serialize_skill(skill):
        value = skill_values.get(skill.id, skill.base_value)
        if skill.name in {'Own Language', 'English'}:
            value = education
        return {
            'id': skill.id,
            'name': gettext(skill.name),
            'description': gettext(skill.description),
            'value': value,
            'base_value': skill.base_value,
            'is_default': value == skill.base_value,
            'is_custom': str(skill.description or '').startswith('Custom skill:') or str(skill.description or '').startswith('Imported custom skill:'),
            'needs_update': skill.id in needs_update_skill_ids,
        }

    def serialize_custom_skill(custom_skill_id, payload):
        sid = int(custom_skill_id)
        value = skill_values.get(sid, payload.get('base_value', 1))
        return {
            'id': sid,
            'name': payload['name'],
            'description': payload.get('description', ''),
            'value': value,
            'base_value': payload.get('base_value', 1),
            'is_default': value == payload.get('base_value', 1),
            'is_custom': True,
            'needs_update': sid in needs_update_skill_ids,
        }

    non_combat_skills = [
        serialize_skill(skill)
        for skill in Skill.objects.exclude(category='combat').exclude(name='Dodge').order_by('name')
        if not _is_custom_skill_record(skill)
    ]
    non_combat_skills.extend(
        serialize_custom_skill(custom_skill_id, payload)
        for custom_skill_id, payload in merged_custom_skills.items()
        if payload.get('category') != 'combat'
    )
    non_combat_skills.sort(key=lambda skill: (-skill['value'], skill['name']))
    combat_skills = [
        serialize_skill(skill)
        for skill in Skill.objects.filter(category='combat').order_by('name')
        if not _is_custom_skill_record(skill)
    ]
    combat_skills.extend(
        serialize_custom_skill(custom_skill_id, payload)
        for custom_skill_id, payload in merged_custom_skills.items()
        if payload.get('category') == 'combat'
    )
    combat_skills.sort(key=lambda skill: (-skill['value'], skill['name']))

    visible_non_combat_skills = [skill for skill in non_combat_skills if not skill['is_default']]
    default_non_combat_skills = [skill for skill in non_combat_skills if skill['is_default']]
    default_non_combat_skills.sort(key=lambda skill: skill['name'].lower())

    return {
        'character': character,
        'skills': visible_non_combat_skills,
        'default_skills': default_non_combat_skills,
        'combat_skills': combat_skills,
        'dodge_value': dexterity // 2,
        'weapons': weapons or [],
        'items': items or [],
        'spells': spells or [],
        'can_add_custom_skill': can_add_custom_skill,
    }


@login_required
def character_list(request):
    """List user's alive characters"""
    characters = Character.objects.filter(
        owner=request.user,
        is_alive=True,
        character_type='PC'
    )
    return render(request, 'characters/list.html', {'characters': characters})


@login_required
def character_detail(request, character_id):
    """Display character sheet"""
    character = get_object_or_404(
        Character,
        id=character_id,
        owner=request.user
    )

    if request.method == 'POST':
        character.player_notes = request.POST.get('player_notes', '').strip()
        character.save(update_fields=['player_notes', 'updated_at'])
        messages.success(request, 'Notes saved.')
        return redirect('characters:detail', character_id=character.id)

    skill_values = {
        char_skill.skill_id: char_skill.value
        for char_skill in CharacterSkill.objects.filter(character=character).select_related('skill')
    }
    weapons = [
        {'name': weapon.weapon.name, 'damage': weapon.weapon.damage, 'is_prepared': weapon.is_prepared}
        for weapon in character.weapons.select_related('weapon').all()
    ]
    items = [
        {'name': item.item.name, 'quantity': item.quantity}
        for item in character.items.select_related('item').all()
    ]
    spells = [
        {'name': spell.spell.name, 'mana_cost': spell.spell.mana_cost}
        for spell in character.spells.select_related('spell').all()
    ]
    sheet = _build_character_sheet_context(
        character=character,
        skill_values=skill_values,
        weapons=weapons,
        items=items,
        spells=spells,
        can_add_custom_skill=request.user.is_keeper() or request.GET.get('creation') == '1',
    )

    context = {
        'sheet': sheet,
        'show_notes': True,
        'notes_editable': True,
        'show_actions': True,
    }

    return render(request, 'characters/detail.html', context)


@login_required
def character_cemetery(request):
    """Show user's dead characters"""
    dead_characters = Character.objects.filter(
        owner=request.user,
        is_alive=False,
        character_type='PC'
    )
    return render(request, 'characters/cemetery.html', {'characters': dead_characters})


@login_required
def character_delete(request, character_id):
    """Delete a character after confirmation."""
    if request.method != 'POST':
        return redirect('characters:detail', character_id=character_id)

    character = get_object_or_404(Character, id=character_id)
    can_delete = character.owner == request.user or request.user.is_keeper()

    if not can_delete:
        messages.error(request, "You don't have permission to delete this character.")
        return redirect('characters:detail', character_id=character_id)

    character_name = character.name
    character.delete()
    messages.success(request, f'Character "{character_name}" deleted successfully.')
    return redirect('characters:list')


@login_required
def character_edit(request, character_id):
    """Edit character (for keepers during game)"""
    character = get_object_or_404(Character, id=character_id)

    # Check if user can edit this character
    # (either owner or keeper of current scenario)
    can_edit = (
        character.owner == request.user or
        request.user.is_keeper()
    )

    if not can_edit:
        messages.error(request, "You don't have permission to edit this character.")
        return redirect('characters:detail', character_id=character_id)

    if request.method == 'POST':
        # Handle AJAX requests
        if request.headers.get('Content-Type') == 'application/json':
            data = json.loads(request.body)
            action = data.get('action')

            # Handle stat updates
            if action is None:
                stat = data.get('stat')
                value = data.get('value')

                if stat and value is not None:
                    if hasattr(character, stat):
                        setattr(character, stat, value)
                        character.save()
                        return JsonResponse({'success': True})

            # Handle adding custom skill
            elif action == 'add_skill':
                skill_name = data.get('skill_name', '').strip()
                skill_value = _to_int(data.get('skill_value'), 0, 0, 100)
                
                if not skill_name:
                    return JsonResponse({'success': False, 'error': 'Skill name is required'})
                
                # Create custom skill
                skill, created = Skill.objects.get_or_create(
                    name=skill_name,
                    defaults={
                        'category': 'general',
                        'base_value': 1,
                        'description': f'Custom skill: {skill_name}',
                    }
                )

                # Add skill to character
                char_skill, created = CharacterSkill.objects.get_or_create(
                    character=character,
                    skill=skill,
                    defaults={'value': skill_value}
                )
                
                if not created:
                    char_skill.value = skill_value
                    char_skill.save()
                
                return JsonResponse({
                    'success': True,
                    'skill_id': skill.id,
                    'message': f'Skill "{skill_name}" added successfully'
                })

        return JsonResponse({'success': False})

    return render(request, 'characters/edit.html', {'character': character})


@login_required
def character_create(request):
    """Create new character with a multi-step wizard."""
    draft = _get_draft(request)
    template_meta = request.session.get(TEMPLATE_WIZARD_META_KEY)
    template_mode = bool(template_meta and _can_manage_templates(request.user))
    template_edit_mode = bool(template_mode and template_meta.get('mode') == 'edit')

    if template_meta and not template_mode:
        request.session.pop(TEMPLATE_WIZARD_META_KEY, None)
        request.session.modified = True
        template_meta = None

    if request.method == 'POST':
        action = request.POST.get('action', 'next')
        step = request.POST.get('step', draft.get('step', WIZARD_STEPS[0]))
        if step not in WIZARD_STEPS:
            step = draft.get('step', WIZARD_STEPS[0])

        if action == 'reset':
            request.session.pop(WIZARD_SESSION_KEY, None)
            messages.success(request, 'Character draft reset.')
            return redirect('characters:create')

        if step == 'basic':
            draft['basic'].update({
                'name': request.POST.get('name', '').strip(),
                'description': request.POST.get('description', '').strip(),
                'occupation': request.POST.get('occupation', '').strip(),
                'age': request.POST.get('age', '').strip(),
            })
        elif step == 'stats':
            stats = draft['stats']
            for field in ['strength', 'constitution', 'dexterity', 'intelligence', 'power', 'size', 'appearance', 'education', 'luck']:
                stats[field] = _to_int(request.POST.get(field), stats.get(field, 0), 0, 100)
            draft['skills'] = _initialize_skill_values(stats['education'], draft.get('skills', {}))
            _sync_custom_skill_values(draft)
        elif step == 'skills':
            updated = {}
            editable_skills = _built_in_skill_queryset()
            try:
                draft['custom_skills'] = _normalize_custom_skills(json.loads(request.POST.get('custom_skills_json', '{}') or '{}'))
            except json.JSONDecodeError:
                draft['custom_skills'] = _normalize_custom_skills(draft.get('custom_skills', {}))
            for skill in editable_skills:
                updated[str(skill.id)] = _to_int(request.POST.get(f'skill_{skill.id}'), skill.base_value, 0, 100)
            for custom_skill_id, payload in draft['custom_skills'].items():
                updated[custom_skill_id] = _to_int(
                    request.POST.get(f'skill_{custom_skill_id}'),
                    draft['skills'].get(custom_skill_id, max(payload.get('base_value', 1), 1)),
                    0,
                    100,
                )
            for skill_name in NON_EDITABLE_SKILL_NAMES:
                skill = Skill.objects.filter(name=skill_name).first()
                if skill:
                    updated[str(skill.id)] = draft['skills'].get(str(skill.id), skill.base_value)
            draft['skills'] = _initialize_skill_values(draft['stats']['education'], updated)
            _sync_custom_skill_values(draft)
        elif step == 'inventory':
            inventory = draft['inventory']
            inventory['cash'] = _to_int(request.POST.get('cash'), inventory.get('cash', 0), 0)
            try:
                weapons_payload = json.loads(request.POST.get('weapons_json', '[]'))
            except json.JSONDecodeError:
                weapons_payload = []
            try:
                items_payload = json.loads(request.POST.get('items_json', '[]'))
            except json.JSONDecodeError:
                items_payload = []

            inventory['weapons'] = []
            for payload in weapons_payload:
                if not isinstance(payload, dict):
                    continue
                weapon_entry = {
                    'weapon_id': _to_int(payload.get('weapon_id'), 0),
                    'custom_name': str(payload.get('custom_name', '')).strip(),
                    'name': str(payload.get('name', '')).strip(),
                    'damage': str(payload.get('damage', '')).strip(),
                    'skill_id': _to_int(payload.get('skill_id'), 0),
                    'skill_name': str(payload.get('skill_name', '')).strip(),
                    'is_prepared': bool(payload.get('is_prepared', False)),
                    'is_default_unarmed': bool(payload.get('is_default_unarmed', False)),
                }
                if weapon_entry['weapon_id'] or weapon_entry['custom_name']:
                    inventory['weapons'].append(weapon_entry)

            inventory['items'] = []
            for payload in items_payload:
                if not isinstance(payload, dict):
                    continue
                item_entry = {
                    'item_id': _to_int(payload.get('item_id'), 0),
                    'custom_name': str(payload.get('custom_name', '')).strip(),
                    'quantity': _to_int(payload.get('quantity'), 0, 0),
                }
                if item_entry['quantity'] > 0 and (item_entry['item_id'] or item_entry['custom_name']):
                    inventory['items'].append(item_entry)

            _ensure_default_unarmed_weapon_entry(draft)

        current_index = WIZARD_STEPS.index(step)
        if action == 'prev':
            draft['step'] = WIZARD_STEPS[max(current_index - 1, 0)]
        elif action == 'goto':
            target_step = request.POST.get('target_step')
            draft['step'] = target_step if target_step in WIZARD_STEPS else step
        elif action == 'save':
            if template_mode:
                payload = _template_payload_from_draft(draft)
                template_name = str(draft.get('basic', {}).get('name', '')).strip() or 'Unnamed Template'

                try:
                    if template_edit_mode:
                        template_id = template_meta.get('template_id')
                        template_record = CharacterTemplate.objects.filter(id=template_id).first()
                        if not template_record:
                            messages.error(request, 'Template not found.')
                            return redirect('characters:templates')
                        template_record.name = template_name
                        template_record.payload = payload
                        template_record.updated_by = request.user
                        template_record.save(update_fields=['name', 'payload', 'updated_by', 'updated_at'])
                    else:
                        template_record = CharacterTemplate.objects.create(
                            name=template_name,
                            payload=payload,
                            created_by=request.user,
                            updated_by=request.user,
                        )

                    request.session.pop(WIZARD_SESSION_KEY, None)
                    request.session.pop(TEMPLATE_WIZARD_META_KEY, None)
                    request.session.modified = True
                    messages.success(request, f'Template "{template_record.name}" saved successfully.')
                    return redirect('characters:templates')
                except DatabaseError:
                    messages.error(request, 'Failed to save template in database.')
                    return redirect('characters:templates')

            character = _create_character_from_draft(request.user, draft)
            request.session.pop(WIZARD_SESSION_KEY, None)
            messages.success(request, f'Character "{character.name}" created successfully.')
            return redirect('characters:detail', character_id=character.id)
        else:
            draft['step'] = WIZARD_STEPS[min(current_index + 1, len(WIZARD_STEPS) - 1)]

        _save_draft(request, draft)
        return redirect('characters:create')

    requested_step = request.GET.get('step')
    if requested_step in WIZARD_STEPS:
        draft['step'] = requested_step
        _save_draft(request, draft)

    skill_options = _build_skill_options_from_draft(draft)
    existing_categories = []
    for category_key, category_label in [('mutual', 'Mutual'), ('general', 'General'), ('combat', 'Combat'), ('language', 'Language')]:
        if any(skill['category'] == category_key for skill in skill_options):
            existing_categories.append((category_key, category_label))

    mythos_skill = Skill.objects.filter(name='Cthulhu Mythos').first()
    mythos_value = draft['skills'].get(str(mythos_skill.id), 0) if mythos_skill else 0
    derived_stats = _derive_secondary_stats(draft['stats'], mythos_value)
    combat_skill_options = _build_combat_skill_options_from_draft(draft)
    preview_character = type('PreviewCharacter', (), {
        'id': None,
        'name': draft['basic'].get('name') or 'Unnamed Character',
        'occupation': draft['basic'].get('occupation', ''),
        'age': draft['basic'].get('age') or None,
        'description': draft['basic'].get('description', ''),
        'cash': _to_int(draft.get('inventory', {}).get('cash'), 0, 0),
        'is_alive': True,
        'hp_current': derived_stats['hp_current'],
        'hp_max': derived_stats['hp_max'],
        'mp_current': derived_stats['mp_current'],
        'mp_max': derived_stats['mp_max'],
        'sanity_current': derived_stats['sanity_current'],
        'sanity_max': derived_stats['sanity_max'],
        'luck': draft['stats'].get('luck', 0),
        'strength': draft['stats'].get('strength', 0),
        'constitution': draft['stats'].get('constitution', 0),
        'dexterity': draft['stats'].get('dexterity', 0),
        'intelligence': draft['stats'].get('intelligence', 0),
        'power': draft['stats'].get('power', 0),
        'size': draft['stats'].get('size', 0),
        'appearance': draft['stats'].get('appearance', 0),
        'education': draft['stats'].get('education', 0),
        'player_notes': '',
    })()
    preview_sheet = _build_character_sheet_context(
        character=preview_character,
        skill_values={int(key): value for key, value in draft['skills'].items()},
        weapons=_normalize_preview_weapons(draft['inventory']['weapons']),
        items=_normalize_preview_items(draft['inventory']['items']),
        spells=[],
        can_add_custom_skill=False,
        custom_skills=draft.get('custom_skills', {}),
    )

    context = {
        'wizard_steps': WIZARD_STEPS,
        'current_step': draft['step'],
        'current_step_index': WIZARD_STEPS.index(draft['step']),
        'draft': draft,
        'skill_options': skill_options,
        'weapon_templates': list(Weapon.objects.order_by('name').values('id', 'name', 'damage', 'skill_name')),
        'item_templates': list(Item.objects.order_by('name').values('id', 'name')),
        'combat_skill_options': combat_skill_options,
        'skill_categories': existing_categories,
        'derived_stats': derived_stats,
        'preview_sheet': preview_sheet,
        # wizard URL context
        'wizard_form_url': reverse('characters:create'),
        'wizard_export_url': reverse('characters:create_export_json'),
        'wizard_import_url': reverse('characters:create_import_json'),
        'wizard_back_url': reverse('characters:templates') if template_mode else reverse('characters:list'),
        'edit_mode': template_edit_mode,
        'show_reset': not template_mode,
        'wizard_title': 'Edit Template' if template_edit_mode else ('Create Template' if template_mode else 'Character Creation Wizard'),
        'wizard_back_text': 'Back to Templates' if template_mode else 'Back to List',
        'final_submit_label': 'Save Template' if template_mode else 'Create Character',
        'show_change_history': False,
        'enable_status_adjustments': False,
    }
    return render(request, 'characters/create.html', context)


@login_required
def character_import_json(request):
    """Import character draft JSON into the creation wizard."""
    if request.method != 'POST':
        return redirect('characters:create')

    uploaded_file = request.FILES.get('json_file')
    if not uploaded_file:
        messages.error(request, 'Please choose a JSON file to import.')
        return redirect('characters:create')

    try:
        payload = json.loads(uploaded_file.read().decode('utf-8'))
        draft = _draft_from_import(payload)
        draft['step'] = 'review'
        _save_draft(request, draft)
        messages.success(request, 'Character draft imported successfully.')
    except (UnicodeDecodeError, json.JSONDecodeError):
        messages.error(request, 'Invalid JSON file.')

    return redirect('characters:create')


@login_required
def character_export_json(request):
    """Export current character draft JSON from the creation wizard."""
    draft = _get_draft(request)
    response = HttpResponse(
        json.dumps(_export_payload_from_draft(draft), indent=2, ensure_ascii=False),
        content_type='application/json',
    )
    response['Content-Disposition'] = 'attachment; filename="character_draft.json"'
    return response


TEMPLATE_WIZARD_META_KEY = 'template_wizard_meta'


def _can_manage_templates(user):
    return bool(
        getattr(user, 'is_superuser', False)
        or (hasattr(user, 'is_keeper') and user.is_keeper())
    )


def _load_character_templates():
    """Read character templates from the database for template cards."""
    templates = []
    for template in CharacterTemplate.objects.order_by('name', 'id'):
        data = template.payload if isinstance(template.payload, dict) else {}
        try:
            info = data.get('character_info', {})
            chars = data.get('characteristics', {})
            skills = data.get('skills', {})
            status_data = data.get('status', {}) if isinstance(data.get('status'), dict) else {}
            sanity_data = status_data.get('Sanity', {}) if isinstance(status_data.get('Sanity'), dict) else {}
            hp_max = max((_to_int(chars.get('STR')) + _to_int(chars.get('CON'))) // 10, 1)
            mp_max = max(_to_int(chars.get('POW')) // 5, 1)
            sanity_max = max(99 - _to_int(skills.get('Cthulhu_Mythos'), 0, 0, 99), 0)
            sanity_current = _to_int(sanity_data.get('current'), min(_to_int(chars.get('POW')), sanity_max), 0, sanity_max)
            top_skills = sorted(
                [(gettext(name.replace('_', ' ')), _to_int(value)) for name, value in skills.items() if _to_int(value) > 25],
                key=lambda x: -x[1],
            )[:6]
            templates.append({
                'id': template.id,
                'name': info.get('name', template.name),
                'occupation': info.get('occupation', ''),
                'age': info.get('age', ''),
                'description': data.get('description', ''),
                'STR': _to_int(chars.get('STR')),
                'CON': _to_int(chars.get('CON')),
                'DEX': _to_int(chars.get('DEX')),
                'INT': _to_int(chars.get('INT')),
                'APP': _to_int(chars.get('APP')),
                'POW': _to_int(chars.get('POW')),
                'SIZ': _to_int(chars.get('SIZ')),
                'EDU': _to_int(chars.get('EDU')),
                'luck': _to_int(chars.get('Luck')),
                'hp_max': hp_max,
                'mp_max': mp_max,
                'sanity': sanity_current,
                'top_skills': top_skills,
                'weapons': [w.get('name', '') for w in data.get('weapons', []) if isinstance(w, dict)],
            })
        except (TypeError, ValueError, KeyError):
            continue
    return templates


@login_required
def character_templates(request):
    """Show character templates list for all users."""
    if request.session.get(TEMPLATE_WIZARD_META_KEY):
        request.session.pop(TEMPLATE_WIZARD_META_KEY, None)
        request.session.pop(WIZARD_SESSION_KEY, None)
        request.session.modified = True

    return render(request, 'characters/templates.html', {
        'templates': _load_character_templates(),
        'can_manage_templates': _can_manage_templates(request.user),
    })


@login_required
def character_use_template(request, template_id):
    """Load a character template into the character creation wizard draft."""
    if request.method != 'POST':
        return redirect('characters:templates')

    template = get_object_or_404(CharacterTemplate, id=template_id)
    payload = template.payload if isinstance(template.payload, dict) else {}
    draft = _draft_from_import(payload)
    draft['step'] = 'basic'

    request.session[WIZARD_SESSION_KEY] = draft
    request.session.pop(TEMPLATE_WIZARD_META_KEY, None)
    request.session.modified = True
    messages.success(request, f'Template "{template.name}" loaded!')
    return redirect('characters:create')


@login_required
def template_create_wizard(request):
    """Start character template creation flow for keepers/admins."""
    if not _can_manage_templates(request.user):
        messages.error(request, 'Only keepers/admins can manage templates.')
        return redirect('characters:templates')

    request.session[WIZARD_SESSION_KEY] = _default_draft()
    request.session[TEMPLATE_WIZARD_META_KEY] = {'mode': 'create'}
    request.session.modified = True
    return redirect('characters:create')


@login_required
def template_edit_wizard(request, template_id):
    """Start character template edit flow for keepers/admins."""
    if not _can_manage_templates(request.user):
        messages.error(request, 'Only keepers/admins can manage templates.')
        return redirect('characters:templates')

    template = CharacterTemplate.objects.filter(id=template_id).first()
    if not template:
        messages.error(request, 'Template not found.')
        return redirect('characters:templates')

    payload = template.payload if isinstance(template.payload, dict) else {}
    draft = _draft_from_import(payload)
    draft['step'] = 'basic'
    request.session[WIZARD_SESSION_KEY] = draft
    request.session[TEMPLATE_WIZARD_META_KEY] = {'mode': 'edit', 'template_id': template.id}
    request.session.modified = True
    return redirect('characters:create')


@login_required
def template_delete(request, template_id):
    """Delete a character template for keepers/admins."""
    if request.method != 'POST':
        return redirect('characters:templates')

    if not _can_manage_templates(request.user):
        messages.error(request, 'Only keepers/admins can manage templates.')
        return redirect('characters:templates')

    template = CharacterTemplate.objects.filter(id=template_id).first()
    if not template:
        messages.error(request, 'Template not found.')
        return redirect('characters:templates')

    template_name = template.name
    template.delete()
    messages.success(request, f'Template "{template_name}" deleted successfully.')
    return redirect('characters:templates')


def _skill_name_to_export_key(skill_name, category=None):
    mapping = {
        'Fighting (Brawl)': 'Fighting_Brawl',
        'Firearms (Rifle/Shotgun)': 'Firearms_Rifle_Shotgun',
        'Firearms (Handgun)': 'Firearms_Handgun',
        'Firearms (Bow/Crossbow)': 'Firearms_Bow_Crossbow',
        'Own Language': 'Language_English_Own',
        'Foreign Language': 'Language_Italian',
        'Repair (Electrical)': 'Repair_Electrical',
        'Repair (Mechanical)': 'Repair_Mechanical',
        'Cthulhu Mythos': 'Cthulhu_Mythos',
    }
    if skill_name in mapping:
        return mapping[skill_name]
    if category == 'language' and not str(skill_name).startswith('Language '):
        return 'Language_' + '_'.join(str(skill_name).replace('(', '').replace(')', '').replace('/', ' ').replace('-', ' ').split())
    normalized = skill_name.replace('(', '').replace(')', '').replace('/', ' ').replace('-', ' ')
    return '_'.join(normalized.split())


def _template_payload_from_draft(draft):
    stats = draft.get('stats', {})
    skills = draft.get('skills', {})
    basic = draft.get('basic', {})
    draft = _sync_custom_skill_values(draft)
    skills_by_id = {str(skill.id): skill for skill in Skill.objects.all()}
    exported_skills = {}
    for skill_id, value in skills.items():
        skill_key = str(skill_id)
        skill = skills_by_id.get(skill_key)
        if skill:
            exported_skills[_skill_name_to_export_key(skill.name, skill.category)] = _to_int(value, skill.base_value, 0, 100)
            continue
        custom_skill = draft.get('custom_skills', {}).get(skill_key)
        if custom_skill:
            exported_skills[_skill_name_to_export_key(custom_skill['name'], custom_skill['category'])] = _to_int(
                value,
                custom_skill.get('base_value', 1),
                0,
                100,
            )

    return {
        'character_info': {
            'name': basic.get('name', ''),
            'occupation': basic.get('occupation', ''),
            'age': basic.get('age', ''),
        },
        'characteristics': {
            'STR': _to_int(stats.get('strength'), 0, 0, 100),
            'CON': _to_int(stats.get('constitution'), 0, 0, 100),
            'DEX': _to_int(stats.get('dexterity'), 0, 0, 100),
            'INT': _to_int(stats.get('intelligence'), 0, 0, 100),
            'APP': _to_int(stats.get('appearance'), 0, 0, 100),
            'POW': _to_int(stats.get('power'), 0, 0, 100),
            'SIZ': _to_int(stats.get('size'), 0, 0, 100),
            'EDU': _to_int(stats.get('education'), 0, 0, 100),
            'Luck': _to_int(stats.get('luck'), 0, 0, 100),
        },
        'skills': exported_skills,
        'weapons': [
            {
                'name': w.get('name') or w.get('custom_name', ''),
                'damage': w.get('damage', ''),
                'is_prepared': bool(w.get('is_prepared', False)),
            }
            for w in draft.get('inventory', {}).get('weapons', [])
            if not w.get('is_default_unarmed')
        ],
        'description': basic.get('description', ''),
        'inventory': [
            item.get('name') or item.get('custom_name', '')
            for item in draft.get('inventory', {}).get('items', [])
            if (item.get('name') or item.get('custom_name'))
        ],
    }


def _status_from_draft(draft):
    """Compute status values from stats plus optional review-step adjustments."""
    draft_stats = draft.get('stats', {})
    draft_adjustments = draft.get('adjustments', {})
    mythos_skill = Skill.objects.filter(name='Cthulhu Mythos').first()
    mythos_value = draft.get('skills', {}).get(str(mythos_skill.id), 0) if mythos_skill else 0
    derived = _derive_secondary_stats(draft_stats, mythos_value)

    hp = _to_int(
        derived['hp_current'] + _to_int(draft_adjustments.get('hp'), 0, -99, 99),
        derived['hp_current'],
        0,
        derived['hp_max'],
    )
    mp = _to_int(
        derived['mp_current'] + _to_int(draft_adjustments.get('mp'), 0, -99, 99),
        derived['mp_current'],
        0,
        derived['mp_max'],
    )
    sanity = _to_int(
        derived['sanity_current'] + _to_int(draft_adjustments.get('sanity'), 0, -99, 99),
        derived['sanity_current'],
        0,
        derived['sanity_max'],
    )

    return {
        'HP': {'max': derived['hp_max'], 'current': hp},
        'MP': {'max': derived['mp_max'], 'current': mp},
        'Sanity': {'max': derived['sanity_max'], 'current': sanity},
    }


def _create_npc_character_from_draft(user, draft):
    """Create a Character (type=NPC) from a wizard draft, applying HP/MP/SAN adjustments."""
    stats = draft['stats']
    basic = draft['basic']
    adjustments = draft.get('adjustments', {})

    base_stats = {
        'strength': _to_int(stats.get('strength'), 0, 0, 100),
        'constitution': _to_int(stats.get('constitution'), 0, 0, 100),
        'dexterity': _to_int(stats.get('dexterity'), 0, 0, 100),
        'intelligence': _to_int(stats.get('intelligence'), 0, 0, 100),
        'power': _to_int(stats.get('power'), 0, 0, 100),
        'size': _to_int(stats.get('size'), 0, 0, 100),
        'appearance': _to_int(stats.get('appearance'), 0, 0, 100),
        'education': _to_int(stats.get('education'), 0, 0, 100),
        'luck': _to_int(stats.get('luck'), 0, 0, 100),
    }

    skill_values, custom_skill_id_map = _resolve_skill_values_for_storage(draft, base_stats['education'])
    cthulhu_mythos = 0
    for skill in Skill.objects.filter(name='Cthulhu Mythos'):
        cthulhu_mythos = _to_int(skill_values.get(str(skill.id), 0), 0, 0, 99)
        break

    derived = _derive_secondary_stats(base_stats, cthulhu_mythos)

    hp_current = _to_int(
        derived['hp_current'] + _to_int(adjustments.get('hp'), 0, -99, 99),
        derived['hp_current'], 0, derived['hp_max'],
    )
    mp_current = _to_int(
        derived['mp_current'] + _to_int(adjustments.get('mp'), 0, -99, 99),
        derived['mp_current'], 0, derived['mp_max'],
    )
    sanity_current = _to_int(
        derived['sanity_current'] + _to_int(adjustments.get('sanity'), 0, -99, 99),
        derived['sanity_current'], 0, derived['sanity_max'],
    )

    character = Character.objects.create(
        owner=user,
        character_type='NPC',
        is_alive=True,
        name=basic.get('name') or 'Unnamed NPC',
        description=basic.get('description', ''),
        occupation=basic.get('occupation', ''),
        age=_to_int(basic.get('age'), None) if str(basic.get('age', '')).strip() else None,
        strength=base_stats['strength'],
        constitution=base_stats['constitution'],
        dexterity=base_stats['dexterity'],
        intelligence=base_stats['intelligence'],
        power=base_stats['power'],
        size=base_stats['size'],
        appearance=base_stats['appearance'],
        education=base_stats['education'],
        hp_current=hp_current,
        hp_max=derived['hp_max'],
        mp_current=mp_current,
        mp_max=derived['mp_max'],
        sanity_current=sanity_current,
        sanity_max=derived['sanity_max'],
        sanity_start=sanity_current,
        luck=base_stats['luck'],
        movement=0,
        build=0,
        damage_bonus='0',
        cash=_to_int(draft.get('inventory', {}).get('cash'), 0, 0),
    )

    skills_by_id = {skill.id: skill for skill in Skill.objects.all()}
    CharacterSkill.objects.bulk_create([
        CharacterSkill(
            character=character,
            skill=skills_by_id[skill_id],
            value=_to_int(value, skills_by_id[skill_id].base_value, 0, 100),
        )
        for skill_id_str, value in skill_values.items()
        if (skill_id := _to_int(skill_id_str, None)) in skills_by_id
    ])

    inventory = draft.get('inventory', {})
    for payload in inventory.get('weapons', []):
        selected_skill_id = str(payload.get('skill_id', ''))
        if selected_skill_id in custom_skill_id_map:
            selected_skill = Skill.objects.filter(id=custom_skill_id_map[selected_skill_id]).first()
        else:
            selected_skill = Skill.objects.filter(id=_to_int(payload.get('skill_id'), -1)).first()
        selected_skill_name = selected_skill.name if selected_skill else str(payload.get('skill_name') or 'Custom').strip()
        selected_skill_value = skill_values.get(str(selected_skill.id), 0) if selected_skill else 0
        weapon = None
        if payload.get('weapon_id'):
            weapon = Weapon.objects.filter(id=_to_int(payload.get('weapon_id'), -1)).first()
        custom_name = str(payload.get('custom_name', '')).strip()
        if not weapon and custom_name:
            weapon = Weapon.objects.filter(name__iexact=custom_name, skill_name=selected_skill_name).first()
            if not weapon:
                weapon = Weapon.objects.create(
                    name=custom_name,
                    skill_name=selected_skill_name,
                    damage=str(payload.get('damage') or '1D4').strip() or '1D4',
                )
        if weapon:
            CharacterWeapon.objects.create(
                character=character,
                weapon=weapon,
                skill_value=selected_skill_value,
                is_prepared=bool(payload.get('is_prepared', False)),
            )

    for payload in inventory.get('items', []):
        item = None
        if payload.get('item_id'):
            item = Item.objects.filter(id=_to_int(payload.get('item_id'), -1)).first()
        custom_name = str(payload.get('custom_name', '')).strip()
        if not item and custom_name:
            item = Item.objects.filter(name__iexact=custom_name).first()
            if not item:
                item = Item.objects.create(name=custom_name)
        if item:
            qty = _to_int(payload.get('quantity'), 1, 1)
            CharacterItem.objects.create(character=character, item=item, quantity=qty)

    return character


def _load_npc_templates():
    """Read NPC templates from the database."""
    templates = []
    for template in NPCTemplate.objects.order_by('name', 'id'):
        data = template.payload if isinstance(template.payload, dict) else {}
        try:
            info = data.get('character_info', {})
            chars = data.get('characteristics', {})
            skills = data.get('skills', {})
            status_data = data.get('status', {}) if isinstance(data.get('status'), dict) else {}
            hp_data = status_data.get('HP', {}) if isinstance(status_data.get('HP'), dict) else {}
            mp_data = status_data.get('MP', {}) if isinstance(status_data.get('MP'), dict) else {}
            sanity_data = status_data.get('Sanity', {}) if isinstance(status_data.get('Sanity'), dict) else {}
            hp_max = _to_int(hp_data.get('max'), max((_to_int(chars.get('STR')) + _to_int(chars.get('CON'))) // 10, 1), 1)
            mp_max = _to_int(mp_data.get('max'), max(_to_int(chars.get('POW')) // 5, 1), 1)
            sanity_max = _to_int(sanity_data.get('max'), max(99 - _to_int(skills.get('Cthulhu_Mythos'), 0, 0, 99), 0), 0)
            sanity_current = _to_int(sanity_data.get('current'), min(_to_int(chars.get('POW')), sanity_max), 0, sanity_max)
            top_skills = sorted(
                [(gettext(name.replace('_', ' ')), val) for name, val in skills.items() if val > 25],
                key=lambda x: -x[1],
            )[:6]
            templates.append({
                'id': template.id,
                'name': info.get('name', template.name),
                'occupation': info.get('occupation', ''),
                'age': info.get('age', ''),
                'description': data.get('description', ''),
                'STR': chars.get('STR', 0),
                'CON': chars.get('CON', 0),
                'DEX': chars.get('DEX', 0),
                'INT': chars.get('INT', 0),
                'APP': chars.get('APP', 0),
                'POW': chars.get('POW', 0),
                'SIZ': chars.get('SIZ', 0),
                'EDU': chars.get('EDU', 0),
                'luck': chars.get('Luck', 0),
                'hp_max': hp_max,
                'mp_max': mp_max,
                'sanity': sanity_current,
                'top_skills': top_skills,
                'weapons': [w.get('name', '') for w in data.get('weapons', [])],
            })
        except (TypeError, ValueError, KeyError):
            continue
    return templates


@login_required
def npc_templates(request):
    """Show NPC templates for admins/keepers."""
    if not _can_manage_templates(request.user):
        messages.error(request, 'Only keepers/admins can view NPC templates.')
        return redirect('characters:templates')

    if request.session.get(NPC_TEMPLATE_WIZARD_META_KEY):
        request.session.pop(NPC_TEMPLATE_WIZARD_META_KEY, None)
        request.session.pop(NPC_WIZARD_SESSION_KEY, None)
        request.session.modified = True

    return render(request, 'characters/npc_templates.html', {
        'templates': _load_npc_templates(),
        'can_manage_templates': _can_manage_templates(request.user),
    })


@login_required
def npc_use_template(request, template_id):
    """Load an NPC DB template into the creation wizard draft and redirect to NPC wizard."""
    if not _can_manage_templates(request.user):
        messages.error(request, 'Only keepers/admins can use NPC templates.')
        return redirect('characters:npc_templates')

    if request.method != 'POST':
        return redirect('characters:npc_templates')

    template = get_object_or_404(NPCTemplate, id=template_id)
    payload = template.payload if isinstance(template.payload, dict) else {}

    try:
        draft = _draft_from_import(payload)
        draft['step'] = 'basic'
        request.session[NPC_WIZARD_SESSION_KEY] = draft
        request.session.modified = True
        messages.success(request, f'NPC template "{template.name}" loaded! Customize below.')
    except (TypeError, ValueError):
        messages.error(request, 'Failed to load NPC template.')

    return redirect('characters:npc_create')


@login_required
def npc_template_create_wizard(request):
    """Start NPC template creation flow for keepers/admins."""
    if not _can_manage_templates(request.user):
        messages.error(request, 'Only keepers/admins can manage NPC templates.')
        return redirect('characters:npc_templates')

    request.session[NPC_WIZARD_SESSION_KEY] = _default_draft()
    request.session[NPC_TEMPLATE_WIZARD_META_KEY] = {'mode': 'create'}
    request.session.modified = True
    return redirect('characters:npc_create')


@login_required
def npc_template_edit_wizard(request, template_id):
    """Start NPC template edit flow for keepers/admins."""
    if not _can_manage_templates(request.user):
        messages.error(request, 'Only keepers/admins can manage NPC templates.')
        return redirect('characters:npc_templates')

    template = NPCTemplate.objects.filter(id=template_id).first()
    if not template:
        messages.error(request, 'NPC template not found.')
        return redirect('characters:npc_templates')

    payload = template.payload if isinstance(template.payload, dict) else {}
    try:
        draft = _draft_from_import(payload)
    except (TypeError, ValueError):
        messages.error(request, 'NPC template data is invalid.')
        return redirect('characters:npc_templates')

    request.session[NPC_WIZARD_SESSION_KEY] = draft
    request.session[NPC_TEMPLATE_WIZARD_META_KEY] = {'mode': 'edit', 'template_id': template.id}
    request.session.modified = True
    return redirect('characters:npc_create')


@login_required
def npc_template_delete(request, template_id):
    """Delete an NPC DB template for keepers/admins."""
    if request.method != 'POST':
        return redirect('characters:npc_templates')

    if not _can_manage_templates(request.user):
        messages.error(request, 'Only keepers/admins can manage NPC templates.')
        return redirect('characters:npc_templates')

    template = NPCTemplate.objects.filter(id=template_id).first()
    if not template:
        messages.error(request, 'NPC template not found.')
        return redirect('characters:npc_templates')

    template_name = template.name
    template.delete()
    messages.success(request, f'NPC template "{template_name}" deleted successfully.')
    return redirect('characters:npc_templates')


@login_required
def npc_create(request):
    """Shared NPC creation wizard for keepers/admins."""
    if not _can_manage_templates(request.user):
        messages.error(request, 'Only keepers/admins can create NPCs.')
        return redirect('characters:templates')

    draft = request.session.get(NPC_WIZARD_SESSION_KEY)
    template_meta = request.session.get(NPC_TEMPLATE_WIZARD_META_KEY)
    template_mode = bool(template_meta)
    template_edit_mode = bool(template_mode and template_meta.get('mode') == 'edit')

    if not draft:
        draft = _default_draft()
    draft.setdefault('adjustments', {'hp': 0, 'mp': 0, 'sanity': 0, 'luck': 0})

    if request.method == 'POST':
        action = request.POST.get('action', 'next')
        step = request.POST.get('step', draft.get('step', NPC_WIZARD_STEPS[0]))
        if step not in NPC_WIZARD_STEPS:
            step = draft.get('step', NPC_WIZARD_STEPS[0])

        if action == 'reset':
            request.session.pop(NPC_WIZARD_SESSION_KEY, None)
            request.session.pop(NPC_TEMPLATE_WIZARD_META_KEY, None)
            request.session.pop(NPC_WIZARD_TARGET_SCENARIO, None)
            request.session.modified = True
            messages.success(request, 'NPC draft cleared.')
            return redirect('characters:npc_create')

        # Process step data
        if step == 'basic':
            draft['basic'].update({
                'name': request.POST.get('name', '').strip(),
                'description': request.POST.get('description', '').strip(),
                'occupation': request.POST.get('occupation', '').strip(),
                'age': request.POST.get('age', '').strip(),
            })
        elif step == 'stats':
            stats = draft['stats']
            for field in ['strength', 'constitution', 'dexterity', 'intelligence', 'power', 'size', 'appearance', 'education', 'luck']:
                stats[field] = _to_int(request.POST.get(field), stats.get(field, 0), 0, 100)
            draft['skills'] = _initialize_skill_values(stats['education'], draft.get('skills', {}))
            _sync_custom_skill_values(draft)
        elif step == 'skills':
            updated = {}
            editable_skills = _built_in_skill_queryset()
            try:
                draft['custom_skills'] = _normalize_custom_skills(json.loads(request.POST.get('custom_skills_json', '{}') or '{}'))
            except json.JSONDecodeError:
                draft['custom_skills'] = _normalize_custom_skills(draft.get('custom_skills', {}))
            for skill in editable_skills:
                updated[str(skill.id)] = _to_int(request.POST.get(f'skill_{skill.id}'), skill.base_value, 0, 100)
            for custom_skill_id, payload in draft['custom_skills'].items():
                updated[custom_skill_id] = _to_int(
                    request.POST.get(f'skill_{custom_skill_id}'),
                    draft['skills'].get(custom_skill_id, max(payload.get('base_value', 1), 1)),
                    0,
                    100,
                )
            for skill_name in NON_EDITABLE_SKILL_NAMES:
                skill = Skill.objects.filter(name=skill_name).first()
                if skill:
                    updated[str(skill.id)] = draft['skills'].get(str(skill.id), skill.base_value)
            draft['skills'] = _initialize_skill_values(draft['stats']['education'], updated)
            _sync_custom_skill_values(draft)
        elif step == 'inventory':
            inventory = draft['inventory']
            inventory['cash'] = _to_int(request.POST.get('cash'), inventory.get('cash', 0), 0)
            try:
                weapons_payload = json.loads(request.POST.get('weapons_json', '[]'))
            except json.JSONDecodeError:
                weapons_payload = []
            try:
                items_payload = json.loads(request.POST.get('items_json', '[]'))
            except json.JSONDecodeError:
                items_payload = []

            inventory['weapons'] = []
            for payload in weapons_payload:
                if not isinstance(payload, dict):
                    continue
                entry = {
                    'weapon_id': _to_int(payload.get('weapon_id'), 0),
                    'custom_name': str(payload.get('custom_name', '')).strip(),
                    'name': str(payload.get('name', '')).strip(),
                    'damage': str(payload.get('damage', '')).strip(),
                    'skill_id': _to_int(payload.get('skill_id'), 0),
                    'skill_name': str(payload.get('skill_name', '')).strip(),
                    'is_prepared': bool(payload.get('is_prepared', False)),
                    'is_default_unarmed': bool(payload.get('is_default_unarmed', False)),
                }
                if entry['weapon_id'] or entry['custom_name']:
                    inventory['weapons'].append(entry)

            inventory['items'] = []
            for payload in items_payload:
                if not isinstance(payload, dict):
                    continue
                entry = {
                    'item_id': _to_int(payload.get('item_id'), 0),
                    'custom_name': str(payload.get('custom_name', '')).strip(),
                    'quantity': _to_int(payload.get('quantity'), 0, 0),
                }
                if entry['quantity'] > 0 and (entry['item_id'] or entry['custom_name']):
                    inventory['items'].append(entry)

            _ensure_default_unarmed_weapon_entry(draft)
        elif step == 'review':
            draft['adjustments'] = {
                'hp': _to_int(request.POST.get('adjust_hp'), draft.get('adjustments', {}).get('hp', 0), -99, 99),
                'mp': _to_int(request.POST.get('adjust_mp'), draft.get('adjustments', {}).get('mp', 0), -99, 99),
                'sanity': _to_int(request.POST.get('adjust_sanity'), draft.get('adjustments', {}).get('sanity', 0), -99, 99),
                'luck': _to_int(request.POST.get('adjust_luck'), draft.get('adjustments', {}).get('luck', 0), -99, 99),
            }

        current_index = NPC_WIZARD_STEPS.index(step)
        if action == 'prev':
            draft['step'] = NPC_WIZARD_STEPS[max(current_index - 1, 0)]
        elif action == 'goto':
            target_step = request.POST.get('target_step')
            draft['step'] = target_step if target_step in NPC_WIZARD_STEPS else step
        elif action == 'save':
            target_scenario_id = request.session.pop(NPC_WIZARD_TARGET_SCENARIO, None)
            if target_scenario_id:
                # Scenario-flow: create NPC Character and add to scenario
                try:
                    from scenarios.models import Scenario, ScenarioNPC
                    scenario = Scenario.objects.get(id=target_scenario_id)
                    npc_char = _create_npc_character_from_draft(request.user, draft)
                    ScenarioNPC.objects.create(scenario=scenario, npc=npc_char)
                    request.session.pop(NPC_WIZARD_SESSION_KEY, None)
                    request.session.pop(NPC_TEMPLATE_WIZARD_META_KEY, None)
                    request.session.modified = True
                    messages.success(request, f'NPC "{npc_char.name}" created and added to the scenario.')
                    return redirect('scenarios:manage', scenario_id=scenario.id)
                except Exception as e:
                    messages.error(request, f'Failed to add NPC to scenario: {str(e)}')
                    return redirect('characters:npc_create')
            try:
                payload = _template_payload_from_draft(draft)
                payload['status'] = _status_from_draft(draft)
                template_id = (template_meta or {}).get('template_id')
                template_name = str(draft.get('basic', {}).get('name', '')).strip() or 'Unnamed NPC'
                if template_id:
                    template = NPCTemplate.objects.get(id=template_id)
                    template.name = template_name
                    template.payload = payload
                    template.updated_by = request.user
                    template.save()
                    messages.success(request, f'NPC template "{template.name}" updated successfully.')
                else:
                    NPCTemplate.objects.create(
                        name=template_name,
                        payload=payload,
                        created_by=request.user,
                        updated_by=request.user,
                    )
                    messages.success(request, 'NPC template created successfully.')
                request.session.pop(NPC_WIZARD_SESSION_KEY, None)
                request.session.pop(NPC_TEMPLATE_WIZARD_META_KEY, None)
                request.session.modified = True
                return redirect('characters:npc_templates')
            except (ValueError, KeyError, NPCTemplate.DoesNotExist) as e:
                messages.error(request, f'Failed to save NPC template: {str(e)}')
                return redirect('characters:npc_templates')
        else:
            draft['step'] = NPC_WIZARD_STEPS[min(current_index + 1, len(NPC_WIZARD_STEPS) - 1)]

        request.session[NPC_WIZARD_SESSION_KEY] = draft
        request.session.modified = True
        return redirect('characters:npc_create')

    # GET request
    requested_step = request.GET.get('step')
    if requested_step in NPC_WIZARD_STEPS:
        draft['step'] = requested_step

    # Store target scenario if provided via query param
    add_to_scenario = request.GET.get('add_to_scenario')
    if add_to_scenario:
        try:
            request.session[NPC_WIZARD_TARGET_SCENARIO] = int(add_to_scenario)
            request.session.modified = True
        except (ValueError, TypeError):
            pass

    target_scenario_id = request.session.get(NPC_WIZARD_TARGET_SCENARIO)

    request.session[NPC_WIZARD_SESSION_KEY] = draft
    request.session.modified = True

    skill_options = _build_skill_options_from_draft(draft)
    existing_categories = []
    for category_key, category_label in [('mutual', 'Mutual'), ('general', 'General'), ('combat', 'Combat'), ('language', 'Language')]:
        if any(skill['category'] == category_key for skill in skill_options):
            existing_categories.append((category_key, category_label))

    mythos_skill = Skill.objects.filter(name='Cthulhu Mythos').first()
    mythos_value = draft['skills'].get(str(mythos_skill.id), 0) if mythos_skill else 0
    derived_stats = _derive_secondary_stats(draft['stats'], mythos_value)
    hp_current = _to_int(
        derived_stats['hp_current'] + _to_int(draft.get('adjustments', {}).get('hp'), 0, -99, 99),
        derived_stats['hp_current'],
        0,
        derived_stats['hp_max'],
    )
    mp_current = _to_int(
        derived_stats['mp_current'] + _to_int(draft.get('adjustments', {}).get('mp'), 0, -99, 99),
        derived_stats['mp_current'],
        0,
        derived_stats['mp_max'],
    )
    sanity_current = _to_int(
        derived_stats['sanity_current'] + _to_int(draft.get('adjustments', {}).get('sanity'), 0, -99, 99),
        derived_stats['sanity_current'],
        0,
        derived_stats['sanity_max'],
    )
    combat_skill_options = _build_combat_skill_options_from_draft(draft)
    preview_character = type('PreviewCharacter', (), {
        'id': None,
        'name': draft['basic'].get('name') or 'Unnamed NPC',
        'occupation': draft['basic'].get('occupation', ''),
        'age': draft['basic'].get('age') or None,
        'description': draft['basic'].get('description', ''),
        'cash': _to_int(draft.get('inventory', {}).get('cash'), 0, 0),
        'is_alive': True,
        'hp_current': hp_current,
        'hp_max': derived_stats['hp_max'],
        'mp_current': mp_current,
        'mp_max': derived_stats['mp_max'],
        'sanity_current': sanity_current,
        'sanity_max': derived_stats['sanity_max'],
        'luck': draft['stats'].get('luck', 0),
        'strength': draft['stats'].get('strength', 0),
        'constitution': draft['stats'].get('constitution', 0),
        'dexterity': draft['stats'].get('dexterity', 0),
        'intelligence': draft['stats'].get('intelligence', 0),
        'power': draft['stats'].get('power', 0),
        'size': draft['stats'].get('size', 0),
        'appearance': draft['stats'].get('appearance', 0),
        'education': draft['stats'].get('education', 0),
        'player_notes': '',
    })()
    preview_sheet = _build_character_sheet_context(
        character=preview_character,
        skill_values={int(key): value for key, value in draft['skills'].items()},
        weapons=_normalize_preview_weapons(draft['inventory']['weapons']),
        items=_normalize_preview_items(draft['inventory']['items']),
        spells=[],
        can_add_custom_skill=False,
        custom_skills=draft.get('custom_skills', {}),
    )

    # Determine back URL based on context
    if target_scenario_id:
        try:
            wizard_back_url = reverse('scenarios:manage', kwargs={'scenario_id': target_scenario_id})
            wizard_back_text = 'Back to Scenario'
            wizard_title = 'Add NPC to Scenario'
        except Exception:
            wizard_back_url = reverse('characters:npc_templates')
            wizard_back_text = 'Back to NPC Templates'
            wizard_title = 'NPC Wizard'
    elif template_edit_mode:
        wizard_back_url = reverse('characters:npc_templates')
        wizard_back_text = 'Back to NPC Templates'
        wizard_title = 'Edit NPC Template'
    else:
        wizard_back_url = reverse('characters:npc_templates')
        wizard_back_text = 'Back to NPC Templates'
        wizard_title = 'NPC Template Wizard'

    return render(request, 'characters/create.html', {
        'wizard_steps': NPC_WIZARD_STEPS,
        'current_step': draft['step'],
        'current_step_index': NPC_WIZARD_STEPS.index(draft['step']),
        'draft': draft,
        'skill_options': skill_options,
        'weapon_templates': list(Weapon.objects.order_by('name').values('id', 'name', 'damage', 'skill_name')),
        'item_templates': list(Item.objects.order_by('name').values('id', 'name')),
        'combat_skill_options': combat_skill_options,
        'skill_categories': existing_categories,
        'derived_stats': derived_stats,
        'preview_sheet': preview_sheet,
        'wizard_form_url': reverse('characters:npc_create'),
        'wizard_export_url': reverse('characters:npc_export_json'),
        'wizard_import_url': reverse('characters:npc_import_json'),
        'wizard_back_url': wizard_back_url,
        'edit_mode': template_edit_mode,
        'show_reset': True,
        'wizard_title': wizard_title,
        'wizard_back_text': wizard_back_text,
        'final_submit_label': 'Create NPC' if target_scenario_id else 'Save NPC Template',
        'show_change_history': False,
        'enable_status_adjustments': True,
    })


@login_required
def npc_import_json(request):
    """Import NPC JSON file into wizard draft."""
    if not _can_manage_templates(request.user):
        messages.error(request, 'Only keepers/admins can import NPCs.')
        return redirect('characters:npc_templates')

    if request.method != 'POST':
        return redirect('characters:npc_create')

    uploaded_file = request.FILES.get('json_file')
    if not uploaded_file:
        messages.error(request, 'Please choose a JSON file to import.')
        return redirect('characters:npc_create')

    try:
        payload = json.loads(uploaded_file.read().decode('utf-8'))
        draft = _draft_from_import(payload)
        draft['step'] = 'basic'
        request.session[NPC_WIZARD_SESSION_KEY] = draft
        request.session.modified = True
        messages.success(request, 'NPC imported successfully.')
    except (UnicodeDecodeError, json.JSONDecodeError):
        messages.error(request, 'Invalid JSON file.')
    return redirect('characters:npc_create')


@login_required
def npc_export_json(request):
    """Export NPC wizard draft as JSON."""
    if not _can_manage_templates(request.user):
        messages.error(request, 'Only keepers/admins can export NPCs.')
        return redirect('characters:npc_create')

    draft = request.session.get(NPC_WIZARD_SESSION_KEY, _default_draft())
    payload = _export_payload_from_draft(draft)
    payload['status'] = _status_from_draft(draft)

    response = HttpResponse(
        json.dumps(payload, indent=2, ensure_ascii=False),
        content_type='application/json',
    )
    name = draft.get('basic', {}).get('name', 'npc').replace(' ', '_').lower()
    response['Content-Disposition'] = f'attachment; filename="{name}.json"'
    return response


# ── Edit Wizard ───────────────────────────────────────────────────────────────

EDIT_WIZARD_STEPS = ['basic', 'stats', 'skills', 'inventory', 'review']


def _edit_session_key(character_id):
    return f'character_edit_draft_{character_id}'


def _normalize_weapon_entry_for_diff(entry):
    return {
        'name': str(entry.get('name') or entry.get('custom_name') or '').strip(),
        'damage': str(entry.get('damage') or '').strip(),
        'skill': str(entry.get('skill_name') or '').strip(),
        'prepared': bool(entry.get('is_prepared', False)),
    }


def _normalize_item_entry_for_diff(entry):
    return {
        'name': str(entry.get('name') or entry.get('custom_name') or '').strip(),
        'quantity': _to_int(entry.get('quantity'), 0, 0),
    }


def _build_edit_change_entries(character, draft):
    """Compute character changes for history log, excluding HP/MP/SAN adjustments."""
    changes = []
    basic = draft.get('basic', {})
    stats = draft.get('stats', {})

    def add_change(label, before, after):
        before_text = '' if before is None else str(before)
        after_text = '' if after is None else str(after)
        if before_text != after_text:
            changes.append({'field': label, 'before': before_text, 'after': after_text})

    add_change('Name', character.name, basic.get('name') or character.name)
    add_change('Description', character.description or '', basic.get('description', ''))
    add_change('Occupation', character.occupation or '', basic.get('occupation', ''))
    add_change('Age', character.age, _to_int(basic.get('age'), None) if str(basic.get('age', '')).strip() else None)

    stat_mappings = [
        ('STR', 'strength'),
        ('CON', 'constitution'),
        ('DEX', 'dexterity'),
        ('INT', 'intelligence'),
        ('POW', 'power'),
        ('SIZ', 'size'),
        ('APP', 'appearance'),
        ('EDU', 'education'),
        ('LCK', 'luck'),
    ]
    for label, field in stat_mappings:
        add_change(label, getattr(character, field), _to_int(stats.get(field), getattr(character, field), 0, 100))

    skills_by_id = {skill.id: skill for skill in Skill.objects.all()}
    current_skills = {cs.skill_id: cs.value for cs in CharacterSkill.objects.filter(character=character)}
    next_skills = {
        int(skill_id): _to_int(value, 0, 0, 100)
        for skill_id, value in _initialize_skill_values(
            _to_int(stats.get('education'), character.education, 0, 100),
            draft.get('skills', {}),
        ).items()
        if str(skill_id).isdigit()
    }
    for skill_id, next_value in next_skills.items():
        before_value = current_skills.get(skill_id)
        if before_value != next_value and skill_id in skills_by_id:
            add_change(f"Skill: {skills_by_id[skill_id].name}", before_value, next_value)

    current_weapons = sorted([
        _normalize_weapon_entry_for_diff({
            'name': cw.weapon.name,
            'damage': cw.weapon.damage,
            'skill_name': cw.weapon.skill_name,
            'is_prepared': cw.is_prepared,
        })
        for cw in character.weapons.select_related('weapon').all()
    ], key=lambda w: (w['name'], w['damage'], w['skill'], w['prepared']))
    draft_weapons = sorted([
        _normalize_weapon_entry_for_diff(w)
        for w in draft.get('inventory', {}).get('weapons', [])
    ], key=lambda w: (w['name'], w['damage'], w['skill'], w['prepared']))
    if current_weapons != draft_weapons:
        add_change('Weapons', len(current_weapons), len(draft_weapons))

    current_items = sorted([
        _normalize_item_entry_for_diff({'name': ci.item.name, 'quantity': ci.quantity})
        for ci in character.items.select_related('item').all()
    ], key=lambda i: (i['name'], i['quantity']))
    draft_items = sorted([
        _normalize_item_entry_for_diff(i)
        for i in draft.get('inventory', {}).get('items', [])
    ], key=lambda i: (i['name'], i['quantity']))
    if current_items != draft_items:
        add_change('Inventory', len(current_items), len(draft_items))

    return changes


def _load_edit_draft_from_character(character):
    """Build a wizard draft from an existing Character instance."""
    skill_values = {}
    custom_skills = {}
    for char_skill in CharacterSkill.objects.filter(character=character).select_related('skill'):
        if _is_custom_skill_record(char_skill.skill):
            custom_skill_id = _next_custom_skill_key(custom_skills)
            custom_skills[custom_skill_id] = {
                'name': char_skill.skill.name,
                'category': char_skill.skill.category,
                'base_value': char_skill.skill.base_value,
                'description': char_skill.skill.description,
            }
            skill_values[custom_skill_id] = char_skill.value
        else:
            skill_values[str(char_skill.skill_id)] = char_skill.value
    # Keep full stats so preview sheet renders correctly
    stats = {
        'strength': character.strength,
        'constitution': character.constitution,
        'dexterity': character.dexterity,
        'intelligence': character.intelligence,
        'power': character.power,
        'size': character.size,
        'appearance': character.appearance,
        'education': character.education,
        'luck': character.luck,
    }

    weapons = []
    for cw in character.weapons.select_related('weapon').all():
        skill = Skill.objects.filter(name__iexact=cw.weapon.skill_name, category='combat').first()
        weapons.append({
            'weapon_id': cw.weapon.id,
            'custom_name': '',
            'name': cw.weapon.name,
            'damage': cw.weapon.damage,
            'skill_id': skill.id if skill else 0,
            'skill_name': cw.weapon.skill_name,
            'is_prepared': cw.is_prepared,
            'is_default_unarmed': cw.weapon.name == DEFAULT_UNARMED_WEAPON_NAME,
        })

    items = [
        {
            'item_id': ci.item.id,
            'custom_name': ci.item.name,
            'name': ci.item.name,
            'quantity': ci.quantity,
        }
        for ci in character.items.select_related('item').all()
    ]

    draft = {
        'step': EDIT_WIZARD_STEPS[0],
        'basic': {
            'name': character.name,
            'description': character.description or '',
            'occupation': character.occupation or '',
            'age': str(character.age) if character.age is not None else '',
        },
        'stats': stats,
        'skills': skill_values,
        'custom_skills': custom_skills,
        'inventory': {'weapons': weapons, 'items': items, 'cash': int(character.cash or 0)},
        'adjustments': {
            'hp': 0,
            'mp': 0,
            'sanity': 0,
            'luck': 0,
        },
    }
    return _sync_custom_skill_values(_ensure_default_unarmed_weapon_entry(draft))


def _apply_edit_draft_to_character(character, draft):
    """Apply all wizard draft data to an existing Character."""
    basic = draft['basic']
    stats = draft.get('stats', {})

    # Basic info
    character.name = basic.get('name') or character.name
    character.description = basic.get('description', '')
    character.occupation = basic.get('occupation', character.occupation)
    raw_age = str(basic.get('age', '')).strip()
    character.age = _to_int(raw_age, None) if raw_age else None

    # Stats
    character.strength = _to_int(stats.get('strength'), character.strength, 0, 100)
    character.constitution = _to_int(stats.get('constitution'), character.constitution, 0, 100)
    character.dexterity = _to_int(stats.get('dexterity'), character.dexterity, 0, 100)
    character.intelligence = _to_int(stats.get('intelligence'), character.intelligence, 0, 100)
    character.power = _to_int(stats.get('power'), character.power, 0, 100)
    character.size = _to_int(stats.get('size'), character.size, 0, 100)
    character.appearance = _to_int(stats.get('appearance'), character.appearance, 0, 100)
    character.education = _to_int(stats.get('education'), character.education, 0, 100)
    character.luck = _to_int(stats.get('luck'), character.luck, 0, 100)

    # Recalculate derived stats
    skill_values_draft, custom_skill_id_map = _resolve_skill_values_for_storage(draft, character.education)
    cthulhu_mythos = 0
    for skill in Skill.objects.filter(name='Cthulhu Mythos'):
        cthulhu_mythos = _to_int(skill_values_draft.get(str(skill.id), 0), 0, 0, 99)
        break
    derived = _derive_secondary_stats(stats, cthulhu_mythos)
    adjustments = draft.get('adjustments', {})
    hp_delta = _to_int(adjustments.get('hp'), 0, -99, 99)
    mp_delta = _to_int(adjustments.get('mp'), 0, -99, 99)
    sanity_delta = _to_int(adjustments.get('sanity'), 0, -99, 99)
    luck_delta = _to_int(adjustments.get('luck'), 0, -99, 99)

    hp_base = min(character.hp_current, derived['hp_max'])
    mp_base = min(character.mp_current, derived['mp_max'])
    sanity_base = min(character.sanity_current, derived['sanity_max'])

    character.hp_max = derived['hp_max']
    character.hp_current = _to_int(hp_base + hp_delta, hp_base, 0, derived['hp_max'])
    character.mp_max = derived['mp_max']
    character.mp_current = _to_int(mp_base + mp_delta, mp_base, 0, derived['mp_max'])
    character.sanity_max = derived['sanity_max']
    character.sanity_start = derived['sanity_start']
    character.sanity_current = _to_int(sanity_base + sanity_delta, sanity_base, 0, derived['sanity_max'])
    character.luck = _to_int(character.luck + luck_delta, character.luck, 0, 100)

    character.cash = _to_int(draft.get('inventory', {}).get('cash'), character.cash, 0)

    character.save(update_fields=[
        'name', 'description', 'occupation', 'age',
        'strength', 'constitution', 'dexterity', 'intelligence', 'power',
        'size', 'appearance', 'education', 'luck',
        'hp_max', 'hp_current', 'mp_max', 'mp_current',
        'sanity_max', 'sanity_start', 'sanity_current', 'cash', 'updated_at',
    ])

    # Rebuild skills
    skills_by_id = {skill.id: skill for skill in Skill.objects.all()}
    CharacterSkill.objects.filter(character=character).delete()
    CharacterSkill.objects.bulk_create([
        CharacterSkill(
            character=character,
            skill=skills_by_id[skill_id],
            value=_to_int(value, skills_by_id[skill_id].base_value, 0, 100),
        )
        for skill_id_str, value in skill_values_draft.items()
        if (skill_id := _to_int(skill_id_str, None)) in skills_by_id
    ])

    # Rebuild weapons
    character.weapons.all().delete()
    refreshed_skill_values = {cs.skill_id: cs.value for cs in CharacterSkill.objects.filter(character=character)}
    for payload in draft.get('inventory', {}).get('weapons', []):
        selected_skill_id = str(payload.get('skill_id', ''))
        if selected_skill_id in custom_skill_id_map:
            selected_skill = Skill.objects.filter(id=custom_skill_id_map[selected_skill_id]).first()
        else:
            selected_skill = Skill.objects.filter(id=_to_int(payload.get('skill_id'), -1)).first()
        selected_skill_name = selected_skill.name if selected_skill else str(payload.get('skill_name') or '').strip()
        selected_skill_value = refreshed_skill_values.get(selected_skill.id, 0) if selected_skill else 0
        weapon = None
        if payload.get('weapon_id'):
            weapon = Weapon.objects.filter(id=_to_int(payload.get('weapon_id'), -1)).first()
        custom_name = str(payload.get('custom_name', '')).strip()
        if not weapon and custom_name:
            weapon = Weapon.objects.filter(name__iexact=custom_name, skill_name=selected_skill_name).first()
            if not weapon:
                weapon = Weapon.objects.create(
                    name=custom_name,
                    skill_name=selected_skill_name,
                    damage=str(payload.get('damage') or '1D4').strip() or '1D4',
                )
        elif weapon and selected_skill_name and weapon.skill_name != selected_skill_name:
            weapon = (
                Weapon.objects.filter(name=weapon.name, skill_name=selected_skill_name, damage=weapon.damage).first()
                or Weapon.objects.create(name=weapon.name, skill_name=selected_skill_name, damage=weapon.damage)
            )
        if weapon:
            CharacterWeapon.objects.create(
                character=character,
                weapon=weapon,
                skill_value=selected_skill_value,
                is_prepared=bool(payload.get('is_prepared', False)),
            )

    # Rebuild items
    character.items.all().delete()
    for payload in draft.get('inventory', {}).get('items', []):
        qty = _to_int(payload.get('quantity'), 0, 0)
        if qty <= 0:
            continue
        item = None
        if payload.get('item_id'):
            item = Item.objects.filter(id=_to_int(payload.get('item_id'), -1)).first()
        custom_name = str(payload.get('custom_name', '')).strip()
        if not item and custom_name:
            item, _ = Item.objects.get_or_create(name=custom_name, defaults={'description': ''})
        if item:
            CharacterItem.objects.create(character=character, item=item, quantity=qty)


def _build_edit_wizard_context(request, character, draft):
    """Build the template context shared by GET and POST for the edit wizard."""
    current_step = draft['step']
    draft_stats = draft.get('stats', {})
    draft_skills = draft.get('skills', {})
    draft_adjustments = draft.get('adjustments', {'hp': 0, 'mp': 0, 'sanity': 0, 'luck': 0})

    skill_options = _build_skill_options_from_draft(draft)
    combat_skill_options = _build_combat_skill_options_from_draft(draft)
    mythos_skill = Skill.objects.filter(name='Cthulhu Mythos').first()
    mythos_value = draft_skills.get(str(mythos_skill.id), 0) if mythos_skill else 0
    derived_stats = _derive_secondary_stats(draft_stats, mythos_value)

    hp_delta = _to_int(draft_adjustments.get('hp'), 0, -99, 99)
    mp_delta = _to_int(draft_adjustments.get('mp'), 0, -99, 99)
    sanity_delta = _to_int(draft_adjustments.get('sanity'), 0, -99, 99)
    luck_delta = _to_int(draft_adjustments.get('luck'), 0, -99, 99)

    hp_base = min(character.hp_current, derived_stats['hp_max'])
    mp_base = min(character.mp_current, derived_stats['mp_max'])
    sanity_base = min(character.sanity_current, derived_stats['sanity_max'])
    luck_base = _to_int(draft_stats.get('luck', character.luck), character.luck, 0, 100)

    review_current_values = {
        'hp': _to_int(hp_base + hp_delta, hp_base, 0, derived_stats['hp_max']),
        'hp_max': derived_stats['hp_max'],
        'mp': _to_int(mp_base + mp_delta, mp_base, 0, derived_stats['mp_max']),
        'mp_max': derived_stats['mp_max'],
        'sanity': _to_int(sanity_base + sanity_delta, sanity_base, 0, derived_stats['sanity_max']),
        'sanity_max': derived_stats['sanity_max'],
        'luck': _to_int(luck_base + luck_delta, luck_base, 0, 100),
    }

    preview_character = type('PreviewCharacter', (), {
        'id': character.id,
        'name': draft['basic'].get('name') or character.name,
        'occupation': draft['basic'].get('occupation', ''),
        'age': draft['basic'].get('age') or None,
        'description': draft['basic'].get('description', ''),
        'cash': _to_int(draft.get('inventory', {}).get('cash'), character.cash, 0),
        'is_alive': character.is_alive,
        'hp_current': review_current_values['hp'],
        'hp_max': derived_stats['hp_max'],
        'mp_current': review_current_values['mp'],
        'mp_max': derived_stats['mp_max'],
        'sanity_current': review_current_values['sanity'],
        'sanity_max': derived_stats['sanity_max'],
        'luck': review_current_values['luck'],
        'strength': draft_stats.get('strength', character.strength),
        'constitution': draft_stats.get('constitution', character.constitution),
        'dexterity': draft_stats.get('dexterity', character.dexterity),
        'intelligence': draft_stats.get('intelligence', character.intelligence),
        'power': draft_stats.get('power', character.power),
        'size': draft_stats.get('size', character.size),
        'appearance': draft_stats.get('appearance', character.appearance),
        'education': draft_stats.get('education', character.education),
        'player_notes': character.player_notes,
    })()
    preview_sheet = _build_character_sheet_context(
        character=preview_character,
        skill_values={int(k): v for k, v in draft_skills.items() if str(k).lstrip('-').isdigit()},
        weapons=_normalize_preview_weapons(draft['inventory']['weapons']),
        items=_normalize_preview_items(draft['inventory']['items']),
        spells=[],
        can_add_custom_skill=False,
        custom_skills=draft.get('custom_skills', {}),
    )
    existing_categories = []
    for category_key, category_label in [('mutual', 'Mutual'), ('general', 'General'), ('combat', 'Combat'), ('language', 'Language')]:
        if any(skill['category'] == category_key for skill in skill_options):
            existing_categories.append((category_key, category_label))

    is_npc = character.character_type == 'NPC'
    wizard_route = 'characters:npc_edit_wizard' if is_npc else 'characters:edit_wizard'
    export_route = 'characters:npc_edit_wizard_export' if is_npc else 'characters:edit_wizard_export'
    import_route = 'characters:npc_edit_wizard_import' if is_npc else 'characters:edit_wizard_import'

    next_url = request.POST.get('next') or request.GET.get('next')
    if next_url and not url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        next_url = None

    def with_next(url_value):
        if not next_url:
            return url_value
        join_char = '&' if '?' in url_value else '?'
        return f"{url_value}{join_char}{urlencode({'next': next_url})}"

    return {
        'wizard_steps': EDIT_WIZARD_STEPS,
        'current_step': current_step,
        'current_step_index': EDIT_WIZARD_STEPS.index(current_step),
        'draft': draft,
        'weapon_templates': list(Weapon.objects.order_by('name').values('id', 'name', 'damage', 'skill_name')),
        'item_templates': list(Item.objects.order_by('name').values('id', 'name')),
        'combat_skill_options': combat_skill_options,
        'derived_stats': derived_stats,
        'preview_sheet': preview_sheet,
        'skill_options': skill_options,
        'skill_categories': existing_categories,
        'wizard_form_url': with_next(reverse(wizard_route, args=[character.id])),
        'wizard_export_url': with_next(reverse(export_route, args=[character.id])),
        'wizard_import_url': with_next(reverse(import_route, args=[character.id])),
        'wizard_back_url': next_url or reverse('characters:detail', args=[character.id]),
        'wizard_next_url': next_url,
        'edit_mode': True,
        'show_reset': False,
        'wizard_title': 'Edit NPC' if is_npc else 'Edit Character',
        'wizard_back_text': 'Back to Session' if next_url else 'Back to Character',
        'show_change_history': True,
        'enable_status_adjustments': True,
        'review_current_values': review_current_values,
        'character_change_logs': CharacterChangeLog.objects.filter(character=character).select_related('changed_by')[:50],
    }


@login_required
def character_edit_wizard(request, character_id):
    """Multi-step wizard for editing an existing character's basic info and inventory."""
    character = get_object_or_404(Character, id=character_id)
    if character.owner != request.user and not request.user.is_keeper():
        messages.error(request, "You don't have permission to edit this character.")
        return redirect('characters:detail', character_id=character_id)

    session_key = _edit_session_key(character_id)
    is_npc = character.character_type == 'NPC'
    wizard_route = 'characters:npc_edit_wizard' if is_npc else 'characters:edit_wizard'

    next_url = request.POST.get('next') or request.GET.get('next')
    if next_url and not url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        next_url = None

    def wizard_redirect():
        base = reverse(wizard_route, kwargs={'character_id': character_id})
        if not next_url:
            return redirect(base)
        return redirect(f"{base}?{urlencode({'next': next_url})}")

    def get_draft():
        draft = request.session.get(session_key)
        if not draft:
            draft = _load_edit_draft_from_character(character)
        draft.setdefault('basic', {'name': character.name, 'description': '', 'occupation': '', 'age': ''})
        draft.setdefault('stats', {})
        draft.setdefault('skills', {})
        draft.setdefault('custom_skills', _default_custom_skills())
        draft.setdefault('inventory', {'weapons': [], 'items': []})
        draft.setdefault('adjustments', {'hp': 0, 'mp': 0, 'sanity': 0, 'luck': 0})
        draft['inventory'].setdefault('weapons', [])
        draft['inventory'].setdefault('items', [])
        return _sync_custom_skill_values(_ensure_default_unarmed_weapon_entry(draft))

    def save_draft(draft):
        request.session[session_key] = draft
        request.session.modified = True

    if request.method == 'POST':
        action = request.POST.get('action', 'next')
        draft = get_draft()
        step = request.POST.get('step', draft.get('step', EDIT_WIZARD_STEPS[0]))
        if step not in EDIT_WIZARD_STEPS:
            step = draft.get('step', EDIT_WIZARD_STEPS[0])

        if action == 'reset':
            request.session.pop(session_key, None)
            return wizard_redirect()

        if step == 'basic':
            draft['basic'].update({
                'name': request.POST.get('name', '').strip(),
                'description': request.POST.get('description', '').strip(),
                'occupation': request.POST.get('occupation', '').strip(),
                'age': request.POST.get('age', '').strip(),
            })
        elif step == 'stats':
            stats = draft['stats']
            for field in ['strength', 'constitution', 'dexterity', 'intelligence', 'power', 'size', 'appearance', 'education', 'luck']:
                stats[field] = _to_int(request.POST.get(field), stats.get(field, 0), 0, 100)
            draft['skills'] = _initialize_skill_values(stats['education'], draft.get('skills', {}))
            _sync_custom_skill_values(draft)
        elif step == 'skills':
            updated = {}
            editable_skills = _built_in_skill_queryset()
            try:
                draft['custom_skills'] = _normalize_custom_skills(json.loads(request.POST.get('custom_skills_json', '{}') or '{}'))
            except json.JSONDecodeError:
                draft['custom_skills'] = _normalize_custom_skills(draft.get('custom_skills', {}))
            for skill in editable_skills:
                updated[str(skill.id)] = _to_int(request.POST.get(f'skill_{skill.id}'), skill.base_value, 0, 100)
            for custom_skill_id, payload in draft['custom_skills'].items():
                updated[custom_skill_id] = _to_int(
                    request.POST.get(f'skill_{custom_skill_id}'),
                    draft['skills'].get(custom_skill_id, max(payload.get('base_value', 1), 1)),
                    0,
                    100,
                )
            for skill_name in NON_EDITABLE_SKILL_NAMES:
                skill = Skill.objects.filter(name=skill_name).first()
                if skill:
                    updated[str(skill.id)] = draft['skills'].get(str(skill.id), skill.base_value)
            draft['skills'] = _initialize_skill_values(draft['stats']['education'], updated)
            _sync_custom_skill_values(draft)
        elif step == 'inventory':
            inventory = draft['inventory']
            inventory['cash'] = _to_int(request.POST.get('cash'), inventory.get('cash', 0), 0)
            try:
                weapons_payload = json.loads(request.POST.get('weapons_json', '[]'))
            except json.JSONDecodeError:
                weapons_payload = []
            try:
                items_payload = json.loads(request.POST.get('items_json', '[]'))
            except json.JSONDecodeError:
                items_payload = []

            inventory['weapons'] = []
            for payload in weapons_payload:
                if not isinstance(payload, dict):
                    continue
                entry = {
                    'weapon_id': _to_int(payload.get('weapon_id'), 0),
                    'custom_name': str(payload.get('custom_name', '')).strip(),
                    'name': str(payload.get('name', '')).strip(),
                    'damage': str(payload.get('damage', '')).strip(),
                    'skill_id': _to_int(payload.get('skill_id'), 0),
                    'skill_name': str(payload.get('skill_name', '')).strip(),
                    'is_prepared': bool(payload.get('is_prepared', False)),
                    'is_default_unarmed': bool(payload.get('is_default_unarmed', False)),
                }
                if entry['weapon_id'] or entry['custom_name']:
                    inventory['weapons'].append(entry)

            inventory['items'] = []
            for payload in items_payload:
                if not isinstance(payload, dict):
                    continue
                entry = {
                    'item_id': _to_int(payload.get('item_id'), 0),
                    'custom_name': str(payload.get('custom_name', '')).strip(),
                    'quantity': _to_int(payload.get('quantity'), 0, 0),
                }
                if entry['quantity'] > 0 and (entry['item_id'] or entry['custom_name']):
                    inventory['items'].append(entry)

            _ensure_default_unarmed_weapon_entry(draft)
        elif step == 'review':
            draft['adjustments'] = {
                'hp': _to_int(request.POST.get('adjust_hp'), draft.get('adjustments', {}).get('hp', 0), -99, 99),
                'mp': _to_int(request.POST.get('adjust_mp'), draft.get('adjustments', {}).get('mp', 0), -99, 99),
                'sanity': _to_int(request.POST.get('adjust_sanity'), draft.get('adjustments', {}).get('sanity', 0), -99, 99),
                'luck': _to_int(request.POST.get('adjust_luck'), draft.get('adjustments', {}).get('luck', 0), -99, 99),
            }

        current_index = EDIT_WIZARD_STEPS.index(step)
        if action == 'prev':
            draft['step'] = EDIT_WIZARD_STEPS[max(current_index - 1, 0)]
        elif action == 'goto':
            target_step = request.POST.get('target_step')
            draft['step'] = target_step if target_step in EDIT_WIZARD_STEPS else step
        elif action == 'save':
            old_name = character.name
            change_entries = _build_edit_change_entries(character, draft)
            _apply_edit_draft_to_character(character, draft)

            if character.character_type == 'NPC' and old_name != character.name:
                # Keep scenario card headers updated unless a custom per-scenario alias is used.
                from scenarios.models import ScenarioNPC
                ScenarioNPC.objects.filter(npc=character, display_name=old_name).update(display_name=character.name)

            if change_entries:
                CharacterChangeLog.objects.create(
                    character=character,
                    changed_by=request.user,
                    changes=change_entries,
                )
            request.session.pop(session_key, None)
            messages.success(request, f'Character "{character.name}" updated successfully.')
            if next_url:
                return redirect(next_url)
            return redirect('characters:detail', character_id=character.id)
        else:
            draft['step'] = EDIT_WIZARD_STEPS[min(current_index + 1, len(EDIT_WIZARD_STEPS) - 1)]

        save_draft(draft)
        return wizard_redirect()

    # GET
    requested_step = request.GET.get('step')
    draft = get_draft()
    if requested_step in EDIT_WIZARD_STEPS:
        draft['step'] = requested_step
        save_draft(draft)

    context = _build_edit_wizard_context(request, character, draft)
    return render(request, 'characters/create.html', context)


@login_required
def character_edit_wizard_export(request, character_id):
    """Export edit-wizard draft as JSON."""
    character = get_object_or_404(Character, id=character_id, owner=request.user)
    draft = request.session.get(_edit_session_key(character_id)) or _load_edit_draft_from_character(character)
    response = HttpResponse(
        json.dumps(_export_payload_from_draft(draft), indent=2, ensure_ascii=False),
        content_type='application/json',
    )
    name_slug = character.name.replace(' ', '_').lower()
    response['Content-Disposition'] = f'attachment; filename="{name_slug}.json"'
    return response


@login_required
def character_edit_wizard_import(request, character_id):
    """Import JSON into edit-wizard draft."""
    character = get_object_or_404(Character, id=character_id, owner=request.user)
    is_npc = character.character_type == 'NPC'
    wizard_route = 'characters:npc_edit_wizard' if is_npc else 'characters:edit_wizard'
    next_url = request.GET.get('next')
    if next_url and not url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        next_url = None

    def wizard_redirect():
        base = reverse(wizard_route, kwargs={'character_id': character_id})
        if not next_url:
            return redirect(base)
        return redirect(f"{base}?{urlencode({'next': next_url})}")

    if request.method != 'POST':
        return wizard_redirect()
    uploaded_file = request.FILES.get('json_file')
    if not uploaded_file:
        messages.error(request, 'Please choose a JSON file to import.')
        return wizard_redirect()
    try:
        payload = json.loads(uploaded_file.read().decode('utf-8'))
        draft = _draft_from_import(payload)
        draft.setdefault('adjustments', {'hp': 0, 'mp': 0, 'sanity': 0, 'luck': 0})
        draft['step'] = 'review'
        request.session[_edit_session_key(character_id)] = draft
        request.session.modified = True
        messages.success(request, 'Draft imported successfully.')
    except (UnicodeDecodeError, json.JSONDecodeError):
        messages.error(request, 'Invalid JSON file.')
    return wizard_redirect()


