import django.core.validators
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


DEFAULT_STATUS_EFFECTS = [
    {
        "name": "Deep Wound",
        "description": "A serious injury that prevents normal natural healing until treated.",
        "effect_type": "DEEP_WOUND",
        "is_permanent": False,
        "icon_class": "bi-heart-pulse-fill",
        "badge_color": "bg-danger",
        "game_rules_json": {"natural_healing_blocked": True, "weekly_con_roll": True},
    },
    {
        "name": "Near Death",
        "description": "The character is at 0 HP and must keep fighting for survival.",
        "effect_type": "NORMAL",
        "is_permanent": False,
        "icon_class": "bi-emoji-dizzy-fill",
        "badge_color": "bg-warning",
        "game_rules_json": {"con_roll_each_turn": True},
    },
    {
        "name": "Psychological Trauma",
        "description": "The character suffered severe SAN loss and risks an episode of madness.",
        "effect_type": "MADNESS",
        "is_permanent": False,
        "icon_class": "bi-brain",
        "badge_color": "bg-secondary",
        "game_rules_json": {"int_roll_required": True},
    },
    {
        "name": "Stunned",
        "description": "The character is stunned and acts with severe limitations.",
        "effect_type": "NORMAL",
        "is_permanent": False,
        "icon_class": "bi-stars",
        "badge_color": "bg-warning",
        "game_rules_json": {},
    },
    {
        "name": "Restrained",
        "description": "The character is physically restrained or immobilized.",
        "effect_type": "NORMAL",
        "is_permanent": False,
        "icon_class": "bi-universal-access-circle",
        "badge_color": "bg-warning",
        "game_rules_json": {},
    },
    {
        "name": "Poisoned",
        "description": "The character is suffering from poison or venom.",
        "effect_type": "NORMAL",
        "is_permanent": False,
        "icon_class": "bi-capsule-pill",
        "badge_color": "bg-warning",
        "game_rules_json": {},
    },
    {
        "name": "Arachnophobia",
        "description": "An intense fear of spiders.",
        "effect_type": "PHOBIA",
        "is_permanent": True,
        "icon_class": "bi-bug-fill",
        "badge_color": "bg-danger",
        "game_rules_json": {},
    },
    {
        "name": "Acrophobia",
        "description": "An intense fear of heights.",
        "effect_type": "PHOBIA",
        "is_permanent": True,
        "icon_class": "bi-building-fill-exclamation",
        "badge_color": "bg-danger",
        "game_rules_json": {},
    },
    {
        "name": "Claustrophobia",
        "description": "An intense fear of confined spaces.",
        "effect_type": "PHOBIA",
        "is_permanent": True,
        "icon_class": "bi-door-closed-fill",
        "badge_color": "bg-danger",
        "game_rules_json": {},
    },
    {
        "name": "Thanatophobia",
        "description": "An intense fear of death or dying.",
        "effect_type": "PHOBIA",
        "is_permanent": True,
        "icon_class": "bi-moon-stars-fill",
        "badge_color": "bg-danger",
        "game_rules_json": {},
    },
    {
        "name": "Dementia",
        "description": "A lingering state of cognitive breakdown and confusion.",
        "effect_type": "MADNESS",
        "is_permanent": False,
        "icon_class": "bi-brain",
        "badge_color": "bg-secondary",
        "game_rules_json": {},
    },
    {
        "name": "Paranoia",
        "description": "The character becomes suspicious, fearful, and distrustful.",
        "effect_type": "MADNESS",
        "is_permanent": False,
        "icon_class": "bi-eye-fill",
        "badge_color": "bg-secondary",
        "game_rules_json": {},
    },
    {
        "name": "Phobia",
        "description": "A generalized or undefined phobic response.",
        "effect_type": "MADNESS",
        "is_permanent": False,
        "icon_class": "bi-exclamation-triangle-fill",
        "badge_color": "bg-secondary",
        "game_rules_json": {},
    },
    {
        "name": "Kleptomania",
        "description": "An uncontrollable urge to steal.",
        "effect_type": "MANIA",
        "is_permanent": False,
        "icon_class": "bi-handbag-fill",
        "badge_color": "bg-info",
        "game_rules_json": {},
    },
    {
        "name": "Pyromania",
        "description": "An obsessive urge related to fire.",
        "effect_type": "MANIA",
        "is_permanent": False,
        "icon_class": "bi-fire",
        "badge_color": "bg-info",
        "game_rules_json": {},
    },
    {
        "name": "Compulsive Behavior",
        "description": "A recurring compulsive behavior that is difficult to resist.",
        "effect_type": "MANIA",
        "is_permanent": False,
        "icon_class": "bi-arrow-repeat",
        "badge_color": "bg-info",
        "game_rules_json": {},
    },
]


def seed_status_effects(apps, schema_editor):
    StatusEffect = apps.get_model("characters", "StatusEffect")
    for effect in DEFAULT_STATUS_EFFECTS:
        StatusEffect.objects.get_or_create(name=effect["name"], defaults=effect)


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Character',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('character_type', models.CharField(choices=[('PC', 'Player Character'), ('NPC', 'Non-Player Character')], default='PC', max_length=3)),
                ('is_alive', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=100)),
                ('birthplace', models.CharField(blank=True, max_length=100)),
                ('residence', models.CharField(blank=True, max_length=100)),
                ('occupation', models.CharField(blank=True, max_length=100)),
                ('gender', models.CharField(blank=True, max_length=20)),
                ('age', models.IntegerField(blank=True, null=True)),
                ('description', models.TextField(blank=True)),
                ('strength', models.IntegerField(validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)])),
                ('constitution', models.IntegerField(validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)])),
                ('dexterity', models.IntegerField(validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)])),
                ('intelligence', models.IntegerField(validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)])),
                ('power', models.IntegerField(validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)])),
                ('size', models.IntegerField(validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)])),
                ('appearance', models.IntegerField(validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)])),
                ('education', models.IntegerField(validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)])),
                ('hp_current', models.IntegerField()),
                ('hp_max', models.IntegerField()),
                ('mp_current', models.IntegerField()),
                ('mp_max', models.IntegerField()),
                ('sanity_current', models.IntegerField()),
                ('sanity_max', models.IntegerField()),
                ('sanity_start', models.IntegerField()),
                ('luck', models.IntegerField(validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)])),
                ('movement', models.IntegerField(default=9)),
                ('build', models.IntegerField()),
                ('damage_bonus', models.CharField(max_length=10)),
                ('cash', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('player_notes', models.TextField(blank=True)),
                ('keeper_notes', models.TextField(blank=True)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='characters', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='CharacterChangeLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('changes', models.JSONField(default=list)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('changed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='character_change_logs', to=settings.AUTH_USER_MODEL)),
                ('character', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='change_logs', to='characters.character')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='CharacterTemplate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=150)),
                ('payload', models.JSONField(default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_character_templates', to=settings.AUTH_USER_MODEL)),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='updated_character_templates', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['name', 'id'],
            },
        ),
        migrations.CreateModel(
            name='NPCTemplate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=150)),
                ('payload', models.JSONField(default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_npc_templates', to=settings.AUTH_USER_MODEL)),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='updated_npc_templates', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['name', 'id'],
            },
        ),
        migrations.CreateModel(
            name='Item',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('description', models.TextField(blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='MentalDisorder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('description', models.TextField()),
            ],
        ),
        migrations.CreateModel(
            name='Skill',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, unique=True)),
                ('category', models.CharField(choices=[('mutual', 'Mutual'), ('general', 'General'), ('combat', 'Combat'), ('language', 'Language')], max_length=10)),
                ('base_value', models.IntegerField(default=0)),
                ('description', models.TextField()),
            ],
        ),
        migrations.CreateModel(
            name='Spell',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('mana_cost', models.IntegerField()),
                ('description', models.TextField()),
            ],
        ),
        migrations.CreateModel(
            name='StatusEffect',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, unique=True)),
                ('description', models.TextField()),
                ('effect_type', models.CharField(
                    choices=[
                        ('NORMAL', 'Custom Status Effect'),
                        ('PHOBIA', 'Phobia'),
                        ('MADNESS', 'Madness'),
                        ('MANIA', 'Mania'),
                        ('DEEP_WOUND', 'Deep Wound'),
                    ],
                    default='NORMAL',
                    max_length=20,
                )),
                ('badge_color', models.CharField(
                    choices=[
                        ('bg-warning', 'Amber'),
                        ('bg-danger', 'Red'),
                        ('bg-info', 'Blue'),
                        ('bg-secondary', 'Gray'),
                        ('bg-success', 'Green'),
                        ('bg-primary', 'Indigo'),
                    ],
                    default='bg-warning',
                    max_length=20,
                )),
                ('is_permanent', models.BooleanField(default=False, help_text='If true, effect cannot be automatically removed')),
                ('icon_class', models.CharField(default='bi-shield-exclamation', help_text='Bootstrap icon class for display', max_length=50)),
                ('game_rules_json', models.JSONField(blank=True, default=dict, help_text='Custom game rules data')),
            ],
            options={
                'ordering': ['effect_type', 'name'],
            },
        ),
        migrations.CreateModel(
            name='Weapon',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50)),
                ('skill_name', models.CharField(max_length=50)),
                ('damage', models.CharField(max_length=20)),
                ('attacks_per_round', models.IntegerField(default=1)),
                ('range', models.CharField(blank=True, max_length=20)),
                ('ammo', models.IntegerField(blank=True, null=True)),
                ('malfunction', models.IntegerField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='CharacterItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.IntegerField(default=1)),
                ('character', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='characters.character')),
                ('item', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='characters.item')),
            ],
        ),
        migrations.CreateModel(
            name='CharacterMentalDisorder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('character', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='mental_disorders', to='characters.character')),
                ('disorder', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='characters.mentaldisorder')),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='charactermentaldisorder',
            unique_together={('character', 'disorder')},
        ),
        migrations.CreateModel(
            name='CharacterSkill',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('value', models.IntegerField(validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)])),
                ('marked_for_improvement', models.BooleanField(default=False)),
                ('needs_update', models.BooleanField(default=False, help_text='Keeper flag: skill needs update after session')),
                ('character', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='skills', to='characters.character')),
                ('skill', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='characters.skill')),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='characterskill',
            unique_together={('character', 'skill')},
        ),
        migrations.CreateModel(
            name='CharacterSpell',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('character', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='spells', to='characters.character')),
                ('spell', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='characters.spell')),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='characterspell',
            unique_together={('character', 'spell')},
        ),
        migrations.CreateModel(
            name='CharacterStatusEffect',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('remaining_rounds', models.IntegerField()),
                ('acquired_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('character', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='status_effects', to='characters.character')),
                ('status_effect', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='characters.statuseffect')),
            ],
            options={
                'ordering': ['-acquired_at'],
            },
        ),
        migrations.CreateModel(
            name='CharacterWeapon',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('skill_value', models.IntegerField()),
                ('is_prepared', models.BooleanField(default=False)),
                ('character', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='weapons', to='characters.character')),
                ('weapon', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='characters.weapon')),
            ],
        ),
        migrations.RunPython(seed_status_effects, migrations.RunPython.noop),
    ]
