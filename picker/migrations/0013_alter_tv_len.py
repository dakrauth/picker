# Generated by Django 4.0.10 on 2024-09-06 14:49

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("picker", "0012_auto_20191224_1707"),
    ]

    operations = [
        migrations.AlterField(
            model_name="game",
            name="tv",
            field=models.CharField(blank=True, max_length=24, verbose_name="TV"),
        ),
    ]