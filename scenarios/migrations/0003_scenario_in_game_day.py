from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scenarios', '0002_scenario_place_visibility_npc_display'),
    ]

    operations = [
        migrations.AddField(
            model_name='scenario',
            name='in_game_day',
            field=models.PositiveIntegerField(default=1),
        ),
    ]

