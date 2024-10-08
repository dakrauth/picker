# Generated by Django 2.1 on 2018-08-24 17:56

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("picker", "0005_auto_20180804_0926"),
    ]

    operations = [
        migrations.AddField(
            model_name="pickergrouping",
            name="category",
            field=models.CharField(
                choices=[("PUB", "Public"), ("PRT", "Protected"), ("PVT", "Private")],
                default="PVT",
                max_length=3,
            ),
        ),
        migrations.AddField(
            model_name="team",
            name="coach",
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AlterField(
            model_name="alias",
            name="team",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="aliases",
                to="picker.Team",
            ),
        ),
        migrations.AlterField(
            model_name="conference",
            name="league",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="conferences",
                to="picker.League",
            ),
        ),
        migrations.AlterField(
            model_name="division",
            name="conference",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="divisions",
                to="picker.Conference",
            ),
        ),
        migrations.AlterField(
            model_name="team",
            name="conference",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="teams",
                to="picker.Conference",
            ),
        ),
        migrations.AlterField(
            model_name="team",
            name="division",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="teams",
                to="picker.Division",
            ),
        ),
        migrations.AlterField(
            model_name="team",
            name="league",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="teams",
                to="picker.League",
            ),
        ),
        migrations.AlterField(
            model_name="team",
            name="nickname",
            field=models.CharField(blank=True, max_length=50),
        ),
    ]
