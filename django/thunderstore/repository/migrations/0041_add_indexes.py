# Generated by Django 3.1.7 on 2023-11-14 08:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("repository", "0040_add_decompilation_visibility_option"),
    ]

    operations = [
        migrations.AlterField(
            model_name="packageversion",
            name="is_active",
            field=models.BooleanField(db_index=True, default=True),
        ),
        migrations.AddIndex(
            model_name="packageversion",
            index=models.Index(
                fields=["date_created", "id"], name="repository__date_cr_f62328_idx"
            ),
        ),
    ]
