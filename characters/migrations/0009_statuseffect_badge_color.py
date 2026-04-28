from django.db import migrations, models


def backfill_status_effect_badge_colors(apps, schema_editor):
    StatusEffect = apps.get_model('characters', 'StatusEffect')
    color_map = {
        'NORMAL': 'bg-warning',
        'PHOBIA': 'bg-danger',
        'MADNESS': 'bg-secondary',
        'MANIA': 'bg-info',
        'DEEP_WOUND': 'bg-danger',
    }

    for effect in StatusEffect.objects.all():
        effect.badge_color = color_map.get(effect.effect_type, 'bg-secondary')
        effect.save(update_fields=['badge_color'])


class Migration(migrations.Migration):

    dependencies = [
        ('characters', '0008_seed_default_status_effects'),
    ]

    operations = [
        migrations.AddField(
            model_name='statuseffect',
            name='badge_color',
            field=models.CharField(
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
            ),
        ),
        migrations.RunPython(backfill_status_effect_badge_colors, migrations.RunPython.noop),
    ]

