# Generated by Django 3.1.7 on 2024-01-16 02:10

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="VisibilityFlags",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("public_list", models.BooleanField(db_index=True)),
                ("public_detail", models.BooleanField(db_index=True)),
                ("owner_list", models.BooleanField(db_index=True)),
                ("owner_detail", models.BooleanField(db_index=True)),
                ("moderator_list", models.BooleanField(db_index=True)),
                ("moderator_detail", models.BooleanField(db_index=True)),
                ("admin_list", models.BooleanField(db_index=True)),
                ("admin_detail", models.BooleanField(db_index=True)),
            ],
        ),
    ]