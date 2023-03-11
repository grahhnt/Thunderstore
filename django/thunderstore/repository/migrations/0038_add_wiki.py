# Generated by Django 3.1.7 on 2023-03-11 21:15

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("thunderstore_wiki", "0001_initial"),
        ("repository", "0037_add_changelog_field"),
    ]

    operations = [
        migrations.CreateModel(
            name="PackageWiki",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("datetime_created", models.DateTimeField(auto_now_add=True)),
                ("datetime_updated", models.DateTimeField(auto_now=True)),
                (
                    "package",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="wiki",
                        to="repository.package",
                    ),
                ),
                (
                    "wiki",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="package_wiki",
                        to="thunderstore_wiki.wiki",
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="packagewiki",
            constraint=models.UniqueConstraint(
                fields=("package", "wiki"), name="unique_package_wiki"
            ),
        ),
    ]
