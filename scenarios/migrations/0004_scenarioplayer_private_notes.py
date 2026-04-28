from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("scenarios", "0003_scenario_in_game_day"),
    ]

    operations = [
        migrations.AddField(
            model_name="scenarioplayer",
            name="private_notes",
            field=models.TextField(blank=True),
        ),
    ]
