from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def backfill_message_receipts(apps, schema_editor):
    Message = apps.get_model('scenarios', 'Message')
    MessageReceipt = apps.get_model('scenarios', 'MessageReceipt')
    ScenarioPlayer = apps.get_model('scenarios', 'ScenarioPlayer')

    receipts = []
    for message in Message.objects.select_related('scenario', 'recipient', 'sender').all():
        if message.message_type == 'PRIVATE' and message.recipient_id:
            receipts.append(
                MessageReceipt(
                    message_id=message.id,
                    user_id=message.recipient_id,
                    read_at=message.sent_at if message.is_read else None,
                )
            )
            continue

        if message.message_type in {'PUBLIC', 'SYSTEM'}:
            player_ids = ScenarioPlayer.objects.filter(
                scenario_id=message.scenario_id,
                is_active=True,
            ).values_list('player_id', flat=True)
            for player_id in player_ids:
                if player_id == message.sender_id:
                    continue
                receipts.append(
                    MessageReceipt(
                        message_id=message.id,
                        user_id=player_id,
                        read_at=message.sent_at if message.is_read else None,
                    )
                )

    MessageReceipt.objects.bulk_create(receipts, ignore_conflicts=True)


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('scenarios', '0004_scenarioplayer_private_notes'),
    ]

    operations = [
        migrations.CreateModel(
            name='MessageReceipt',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('read_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('message', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='receipts', to='scenarios.message')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='message_receipts', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-message__sent_at', '-created_at'],
                'unique_together': {('message', 'user')},
            },
        ),
        migrations.RunPython(backfill_message_receipts, migrations.RunPython.noop),
    ]

