# Generated by Django 3.1.6 on 2021-04-25 17:28

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0011_playerboardmarking_announced'),
    ]

    operations = [
        migrations.AddField(
            model_name='board',
            name='winner',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='board_winner', to='backend.playerboard'),
        ),
    ]
