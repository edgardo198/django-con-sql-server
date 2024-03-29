# Generated by Django 3.0.1 on 2023-11-09 14:44

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('erp', '0004_category_description'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='category',
            name='description',
        ),
        migrations.AddField(
            model_name='category',
            name='desc',
            field=models.CharField(blank=True, max_length=500, null=True, verbose_name='Descripcion'),
        ),
        migrations.AlterField(
            model_name='product',
            name='cate',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='erp.Category', verbose_name='Categoria'),
        ),
        migrations.AlterField(
            model_name='product',
            name='image',
            field=models.ImageField(blank=True, null=True, upload_to='product/%Y/%m/%d', verbose_name='Imagen'),
        ),
        migrations.AlterField(
            model_name='product',
            name='pvp',
            field=models.DecimalField(decimal_places=2, default=0.0, max_digits=9, verbose_name='Precio de Venta'),
        ),
    ]
