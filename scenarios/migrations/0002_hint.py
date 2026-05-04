from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scenarios', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Hint',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(blank=True, max_length=120)),
                ('text', models.TextField()),
                ('audience', models.CharField(choices=[('PLAYER', 'Player'), ('KEEPER', 'Keeper')], max_length=10)),
                ('sort_order', models.PositiveIntegerField(default=0)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['audience', 'sort_order', 'id'],
            },
        ),
    ]

