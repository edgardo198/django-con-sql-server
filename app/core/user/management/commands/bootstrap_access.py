import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils.crypto import get_random_string

from app.core.user.access import ROLE_SUPER_ADMIN, ensure_role_groups


class Command(BaseCommand):
    help = 'Crea los grupos base de acceso y un usuario super admin inicial.'

    def add_arguments(self, parser):
        parser.add_argument('--username', default=os.getenv('SUPERADMIN_USERNAME', 'superadmin'))
        parser.add_argument('--email', default=os.getenv('SUPERADMIN_EMAIL', 'superadmin@local.test'))
        parser.add_argument('--password', default=os.getenv('SUPERADMIN_PASSWORD'))

    def handle(self, *args, **options):
        groups = ensure_role_groups()
        password = options['password'] or get_random_string(20)
        user_model = get_user_model()

        user, created = user_model.objects.get_or_create(
            username=options['username'],
            defaults={
                'email': options['email'],
                'is_superuser': True,
                'is_staff': True,
                'is_active': True,
                'first_name': 'Super',
                'last_name': 'Admin',
            },
        )

        updated_fields = []
        if user.email != options['email']:
            user.email = options['email']
            updated_fields.append('email')
        if not user.is_superuser:
            user.is_superuser = True
            updated_fields.append('is_superuser')
        if not user.is_staff:
            user.is_staff = True
            updated_fields.append('is_staff')
        if not user.is_active:
            user.is_active = True
            updated_fields.append('is_active')

        user.set_password(password)
        updated_fields.append('password')
        user.save(update_fields=updated_fields)
        user.groups.add(groups[ROLE_SUPER_ADMIN])

        if created:
            self.stdout.write(self.style.SUCCESS('Super admin creado correctamente.'))
        else:
            self.stdout.write(self.style.WARNING('Super admin actualizado correctamente.'))

        self.stdout.write('username={}'.format(user.username))
        self.stdout.write('email={}'.format(user.email))
        self.stdout.write('password={}'.format(password))
