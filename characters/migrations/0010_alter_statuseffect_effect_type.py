from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('characters', '0009_statuseffect_badge_color'),
    ]

    operations = [
        migrations.AlterField(
            model_name='statuseffect',
            name='effect_type',
            field=models.CharField(
                choices=[
                    ('NORMAL', 'Custom Status Effect'),
                    ('PHOBIA', 'Phobia'),
                    ('MADNESS', 'Madness'),
                    ('MANIA', 'Mania'),
                    ('DEEP_WOUND', 'Deep Wound'),
                ],
                default='NORMAL',
                max_length=20,
            ),
        ),
    ]

