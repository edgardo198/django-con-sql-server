# Generated by Django 3.0.1 on 2023-11-14 21:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('erp', '0011_auto_20231114_1143'),
    ]

    operations = [
        migrations.AlterField(
            model_name='client',
            name='gender',
            field=models.CharField(choices=[('male', 'Masculino'), ('female', 'Femenino')], default='male', max_length=13, verbose_name='Sexo'),
        ),
    ]