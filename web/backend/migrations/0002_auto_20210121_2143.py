# Generated by Django 3.1.3 on 2021-01-22 05:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='board',
            name='forced_goals',
            field=models.CharField(default='', max_length=256),
        ),
        migrations.AlterField(
            model_name='board',
            name='difficulty',
            field=models.IntegerField(default=2),
        ),
        migrations.AlterField(
            model_name='playerboard',
            name='squares',
            field=models.CharField(default='', max_length=25),
        ),
    ]