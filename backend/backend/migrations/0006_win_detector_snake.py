# Generated by Django 3.1.6 on 2021-02-22 04:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0005_board_win_detector'),
    ]

    operations = [
        migrations.AlterField(
            model_name='board',
            name='win_detector',
            field=models.CharField(choices=[('bingo_standard', 'Standard Bingo rules'), ('hex_snake', 'Hexagonal snaking win'), ('hex_snake_neighborless', 'Hexagonal snaking, no neighbor')], max_length=64, null=True),
        ),
    ]
