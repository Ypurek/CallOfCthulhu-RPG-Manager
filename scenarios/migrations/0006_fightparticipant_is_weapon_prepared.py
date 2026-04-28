from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scenarios', '0005_messagereceipt'),
    ]

    operations = [
        migrations.AddField(
            model_name='fightparticipant',
            name='is_weapon_prepared',
            field=models.BooleanField(default=False),
        ),
    ]

