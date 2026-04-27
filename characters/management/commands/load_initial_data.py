import json
from pathlib import Path
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from characters.models import (
    Character, Skill, CharacterSkill, Weapon, CharacterWeapon,
    Item, CharacterItem, CharacterTemplate
)

User = get_user_model()


class Command(BaseCommand):
    help = 'Load initial data including skills, weapons, and sample character'

    def handle(self, *args, **kwargs):
        # Load skills
        self.stdout.write('Loading skills...')
        skills_file = Path('docs/skills.json')
        with open(skills_file, 'r', encoding='utf-8') as f:
            skills_data = json.load(f)

        for category_name, skills in skills_data.items():
            for skill_name, skill_info in skills.items():
                base_value = skill_info['base_value']
                # Convert percentage string to integer
                if base_value == 'EDU%':
                    # Special case for EDU-based skills
                    base_value = 0  # Will be calculated based on character's EDU
                elif base_value.endswith('%'):
                    base_value = int(base_value[:-1])
                else:
                    base_value = int(base_value)

                skill_name_formatted = skill_name.replace('_', ' ')

                skill, created = Skill.objects.get_or_create(
                    name=skill_name_formatted,
                    defaults={
                        'category': category_name,
                        'base_value': base_value,
                        'description': skill_info.get('description', '')
                    }
                )
                if created:
                    self.stdout.write(f'Created skill: {skill_name_formatted}')

        # Load weapons
        self.stdout.write('Loading weapons...')
        weapons_file = Path('docs/weapons.json')
        with open(weapons_file, 'r', encoding='utf-8') as f:
            weapons_data = json.load(f)

        for weapon_name, weapon_info in weapons_data.items():
            weapon, created = Weapon.objects.get_or_create(
                name=weapon_name,
                defaults={
                    'skill_name': weapon_info.get('skill', ''),
                    'damage': weapon_info.get('damage', ''),
                    'attacks_per_round': weapon_info.get('attacks', 1),
                    'range': weapon_info.get('range', ''),
                    'ammo': weapon_info.get('ammo'),
                    'malfunction': weapon_info.get('malfunction')
                }
            )
            if created:
                self.stdout.write(f'Created weapon: {weapon_name}')

        # Load DB-backed character templates from docs/characters (seed source only)
        self.stdout.write('Loading character templates...')
        templates_dir = Path('docs/characters')
        for template_file in sorted(templates_dir.glob('*.json')):
            try:
                with open(template_file, 'r', encoding='utf-8') as f:
                    template_payload = json.load(f)
            except (OSError, json.JSONDecodeError):
                self.stdout.write(f'Warning: Failed to read template seed {template_file.name}')
                continue

            template_name = (
                template_payload.get('character_info', {}).get('name')
                or template_file.stem.replace('_', ' ').title()
            )
            template, created = CharacterTemplate.objects.get_or_create(
                name=template_name,
                defaults={'payload': template_payload},
            )
            if created:
                self.stdout.write(f'Created template: {template_name}')

        # Create a test user
        self.stdout.write('Creating test users...')
        player_user, created = User.objects.get_or_create(
            username='player1',
            defaults={
                'email': 'player@example.com',
                'role': User.Role.PLAYER,
                'first_name': 'Test',
                'last_name': 'Player'
            }
        )
        if created:
            player_user.set_password('password123')
            player_user.save()
            self.stdout.write('Created test player user: player1 (password: password123)')

        keeper_user, created = User.objects.get_or_create(
            username='keeper1',
            defaults={
                'email': 'keeper@example.com',
                'role': User.Role.KEEPER,
                'first_name': 'Test',
                'last_name': 'Keeper'
            }
        )
        if created:
            keeper_user.set_password('password123')
            keeper_user.save()
            self.stdout.write('Created test keeper user: keeper1 (password: password123)')

        # Create superuser
        if not User.objects.filter(is_superuser=True).exists():
            superuser = User.objects.create_superuser(
                username='admin',
                email='admin@example.com',
                password='admin123',
                role=User.Role.KEEPER
            )
            self.stdout.write('Created superuser: admin (password: admin123)')

        # Load Lois Russo character
        self.stdout.write('Loading Lois Russo character...')
        lois_file = Path('docs/characters/lois_russo.json')
        with open(lois_file, 'r', encoding='utf-8') as f:
            lois_data = json.load(f)

        # Create character
        char_info = lois_data['character_info']
        stats = lois_data['characteristics']
        status = lois_data['status']

        # Calculate cash from Credit Rating
        credit_rating = lois_data['skills'].get('Credit_Rating', 40)
        if credit_rating == 0:
            cash = 0
        elif credit_rating < 10:
            cash = credit_rating * 1
        elif credit_rating < 50:
            cash = credit_rating * 2
        elif credit_rating < 90:
            cash = credit_rating * 5
        else:
            cash = credit_rating * 20

        character, created = Character.objects.get_or_create(
            name='Lois Russo',
            owner=player_user,
            defaults={
                'character_type': 'PC',
                'birthplace': 'New York',
                'residence': 'Arkham',
                'occupation': 'Engineering Student',
                'gender': 'Female',
                'age': 19,
                'description': 'Athletic build. Short brown hair styled fashionably. Raised in Catholic traditions with a healthy respect for the supernatural. Stubborn, hot-tempered, likes to argue. Never walks under ladders.',

                # Stats
                'strength': stats['STR'],
                'constitution': stats['CON'],
                'dexterity': stats['DEX'],
                'intelligence': stats['INT'],
                'power': stats['POW'],
                'size': stats['SIZ'],
                'appearance': stats['APP'],
                'education': stats['EDU'],

                # Status
                'hp_current': status['HP']['current'],
                'hp_max': status['HP']['max'],
                'mp_current': status['MP']['current'],
                'mp_max': status['MP']['max'],
                'sanity_current': status['Sanity']['current'],
                'sanity_max': status['Sanity']['max'],
                'sanity_start': status['Sanity']['start'],
                'luck': stats['Luck'],

                # Derived
                'movement': stats.get('MOV', 9),
                'build': status['Build'],
                'damage_bonus': '+1D4',
                'cash': cash
            }
        )

        if created:
            self.stdout.write('Created Lois Russo character')

            # Add skills
            for skill_name, skill_value in lois_data['skills'].items():
                skill_name_formatted = skill_name.replace('_', ' ')
                try:
                    skill = Skill.objects.get(name=skill_name_formatted)
                    CharacterSkill.objects.create(
                        character=character,
                        skill=skill,
                        value=skill_value
                    )
                except Skill.DoesNotExist:
                    self.stdout.write(f'Warning: Skill {skill_name_formatted} not found')

            # Add weapons
            for weapon_data in lois_data['weapons']:
                weapon_name = weapon_data['name']
                if weapon_name == 'Рукопашний бій':
                    weapon_name = 'Unarmed'
                elif weapon_name == 'Викидний ніж':
                    weapon_name = 'Switchblade'

                try:
                    weapon = Weapon.objects.get(name=weapon_name)
                    CharacterWeapon.objects.create(
                        character=character,
                        weapon=weapon,
                        skill_value=weapon_data['skill_pct']
                    )
                except Weapon.DoesNotExist:
                    # Create a custom weapon if not found
                    weapon = Weapon.objects.create(
                        name=weapon_name,
                        skill_name='Fighting (Brawl)',
                        damage=weapon_data['damage'],
                        attacks_per_round=weapon_data.get('attacks', 1)
                    )
                    CharacterWeapon.objects.create(
                        character=character,
                        weapon=weapon,
                        skill_value=weapon_data['skill_pct']
                    )

            # Add items
            for item_name in lois_data['inventory']:
                item, _ = Item.objects.get_or_create(name=item_name)
                CharacterItem.objects.create(
                    character=character,
                    item=item,
                    quantity=1
                )

        self.stdout.write(self.style.SUCCESS('Successfully loaded initial data!'))