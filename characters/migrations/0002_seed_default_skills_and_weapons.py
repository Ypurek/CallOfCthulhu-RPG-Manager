import json
from pathlib import Path

from django.db import migrations


SKILL_CATEGORY_OVERRIDES = {
    'Own Language': 'language',
    'Foreign Language': 'language',
}

WEAPON_NAME_BY_KEY = {
    'small_knife': 'Малий ніж',
    'machete': 'Мачете',
    'large_club': 'Великий дрюк',
    'baseball_bat': 'Бейсбольна біта',
    'axe': 'Сокира',
    'revolver_38': 'Револьвер .38',
    'automatic_pistol_45': 'Автоматичний пістолет .45',
    'shotgun_12g_2_barrel': 'Двоствольна рушниця 12 калібру',
    'rifle_30_06': 'Гвинтівка .30-06',
    'bow': 'Лук',
    'hand_grenade': 'Ручна граната',
    'dynamite': 'Динаміт',
    'tommy_gun': 'Томмі-ган',
    'brass_knuckles': 'Кастет',
}

WEAPON_SKILL_BY_KEY = {
    'small_knife': 'Fighting (Brawl)',
    'machete': 'Fighting (Brawl)',
    'large_club': 'Fighting (Brawl)',
    'baseball_bat': 'Fighting (Brawl)',
    'axe': 'Fighting (Brawl)',
    'brass_knuckles': 'Fighting (Brawl)',
    'revolver_38': 'Firearms (Handgun)',
    'automatic_pistol_45': 'Firearms (Handgun)',
    'shotgun_12g_2_barrel': 'Firearms (Rifle/Shotgun)',
    'rifle_30_06': 'Firearms (Rifle/Shotgun)',
    'tommy_gun': 'Firearms (Rifle/Shotgun)',
    'bow': 'Firearms (Bow/Crossbow)',
    'hand_grenade': 'Throw',
    'dynamite': 'Throw',
}


def _base_dir():
    return Path(__file__).resolve().parents[2]


def _load_json(relative_path):
    file_path = _base_dir() / relative_path
    with file_path.open('r', encoding='utf-8') as source:
        return json.load(source)


def _parse_base_value(raw_value):
    value = str(raw_value).strip()
    if value == 'EDU%':
        return 0
    if value.endswith('%'):
        value = value[:-1]
    try:
        return int(value)
    except ValueError:
        return 0


def _compact_damage(raw_damage):
    value = str(raw_damage or '').strip() or '1D3 + DB'
    if len(value) <= 20:
        return value
    compact = value.replace(' / ', '/').replace(' ', '')
    return compact[:20]


def seed_default_skills_and_weapons(apps, schema_editor):
    Skill = apps.get_model('characters', 'Skill')
    Weapon = apps.get_model('characters', 'Weapon')

    skills_data = _load_json('docs/skills.json')
    for category, skills in skills_data.items():
        for skill_name, skill_info in skills.items():
            normalized_category = SKILL_CATEGORY_OVERRIDES.get(skill_name, category)
            Skill.objects.get_or_create(
                name=skill_name,
                defaults={
                    'category': normalized_category,
                    'base_value': _parse_base_value(skill_info.get('base_value', 0)),
                    'description': str(skill_info.get('description', '')).strip(),
                },
            )

    weapons_data = _load_json('docs/weapons.json')
    for key, weapon_info in weapons_data.items():
        weapon_name = WEAPON_NAME_BY_KEY.get(key, key.replace('_', ' ').title())
        # Avoid duplicates because Weapon.name is not unique.
        if Weapon.objects.filter(name__iexact=weapon_name).exists():
            continue

        rounds = weapon_info.get('rounds')
        ammo = rounds if isinstance(rounds, int) and rounds > 0 else None
        Weapon.objects.create(
            name=weapon_name,
            skill_name=WEAPON_SKILL_BY_KEY.get(key, 'Fighting (Brawl)'),
            damage=_compact_damage(weapon_info.get('base_damage')),
            attacks_per_round=1,
            ammo=ammo,
            range='',
            malfunction=None,
        )


def noop_reverse(apps, schema_editor):
    # Keep seeded records when rolling back; deleting may remove user-modified data.
    return


class Migration(migrations.Migration):

    dependencies = [
        ('characters', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_default_skills_and_weapons, noop_reverse),
    ]
