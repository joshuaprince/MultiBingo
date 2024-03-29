# Generated by Django 3.1.6 on 2021-04-25 17:46

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0010_yamlify'),
    ]

    operations = [
        migrations.AddField(
            model_name='board',
            name='winner',
            field=models.OneToOneField(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='winning_board', to='backend.playerboard'),
        ),
        migrations.AddField(
            model_name='playerboardmarking',
            name='announced',
            field=models.BooleanField(default=False),
        ),
    ]
