# Generated by Django 3.0.1 on 2023-11-10 20:35

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('erp', '0008_auto_20231110_0841'),
    ]

    operations = [
        migrations.RenameField(
            model_name='client',
            old_name='birthday',
            new_name='date_birthday',
        ),
    ]