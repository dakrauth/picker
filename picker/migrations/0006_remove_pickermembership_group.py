# Generated by Django 2.0.7 on 2018-07-30 23:43

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('picker', '0005_auto_20180730_1936'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='pickermembership',
            name='group',
        ),
    ]
