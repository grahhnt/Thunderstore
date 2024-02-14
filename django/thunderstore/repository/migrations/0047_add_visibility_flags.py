# Generated by Django 3.1.7 on 2024-01-16 02:10

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("permissions", "__first__"),
        ("repository", "0046_add_submission_cleanup_schedule"),
    ]

    operations = [
        migrations.AddField(
            model_name="packageversion",
            name="visibility",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                to="permissions.visibilityflags",
            ),
        ),
    ]