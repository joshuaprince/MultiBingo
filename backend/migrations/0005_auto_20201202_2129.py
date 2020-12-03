# Generated by Django 3.1.3 on 2020-12-03 05:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0004_playerboard_disconnected_at'),
    ]

    operations = [
        migrations.AlterField(
            model_name='board',
            name='seed',
            field=models.SlugField(max_length=128, unique=True),
        ),
        migrations.AlterUniqueTogether(
            name='playerboard',
            unique_together={('board', 'player_name')},
        ),
    ]
