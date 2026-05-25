# Generated manually for local/web synchronization.

import uuid

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='SyncConflict',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('model_label', models.CharField(db_index=True, max_length=100)),
                ('sync_uuid', models.UUIDField(db_index=True)),
                ('local_updated_at', models.DateTimeField(blank=True, null=True)),
                ('remote_updated_at', models.DateTimeField(blank=True, null=True)),
                ('description', models.TextField()),
                ('resolved', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='SyncIdentity',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('model_label', models.CharField(db_index=True, max_length=100)),
                ('object_id', models.BigIntegerField(db_index=True)),
                ('sync_uuid', models.UUIDField(db_index=True, default=uuid.uuid4, unique=True)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['model_label', 'object_id'],
                'unique_together': {('model_label', 'object_id')},
            },
        ),
        migrations.CreateModel(
            name='SyncOutbox',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('model_label', models.CharField(db_index=True, max_length=100)),
                ('object_id', models.BigIntegerField(blank=True, db_index=True, null=True)),
                ('sync_uuid', models.UUIDField(db_index=True)),
                ('action', models.CharField(choices=[('upsert', 'Crear/actualizar'), ('delete', 'Eliminar')], max_length=10)),
                ('created_at', models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ('processed_at', models.DateTimeField(blank=True, db_index=True, null=True)),
                ('attempt_count', models.PositiveIntegerField(default=0)),
                ('last_attempt_at', models.DateTimeField(blank=True, null=True)),
                ('error', models.TextField(blank=True)),
            ],
            options={
                'ordering': ['created_at', 'id'],
            },
        ),
        migrations.CreateModel(
            name='SyncState',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('remote_url', models.URLField(unique=True)),
                ('last_pull_at', models.DateTimeField(blank=True, null=True)),
                ('last_push_at', models.DateTimeField(blank=True, null=True)),
                ('last_error', models.TextField(blank=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['remote_url'],
            },
        ),
        migrations.CreateModel(
            name='SyncRunLock',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=80, unique=True)),
                ('owner', models.CharField(blank=True, max_length=100)),
                ('locked_until', models.DateTimeField(blank=True, null=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='SyncTombstone',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('model_label', models.CharField(db_index=True, max_length=100)),
                ('sync_uuid', models.UUIDField(db_index=True)),
                ('deleted_at', models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
            ],
            options={
                'ordering': ['deleted_at'],
                'unique_together': {('model_label', 'sync_uuid')},
            },
        ),
    ]
