from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models, transaction
from django.forms import model_to_dict

from app.core.models import BaseModel
from app.core.user.access import (
    ROLE_SUPER_ADMIN,
    can_manage_user,
    get_assignable_role_names,
    get_user_role_priority,
    sort_role_names,
)


class Organization(BaseModel):
    name = models.CharField(max_length=150, unique=True, verbose_name='Nombre')
    code = models.CharField(max_length=30, blank=True, null=True, verbose_name='Codigo')
    rtn = models.CharField(max_length=20, blank=True, null=True, verbose_name='RTN')
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name='Telefono')
    email = models.EmailField(blank=True, null=True, verbose_name='Correo')
    address = models.CharField(max_length=255, blank=True, null=True, verbose_name='Direccion')
    image = models.ImageField(upload_to='organization/%Y/%m/%d', null=True, blank=True, verbose_name='Logo')
    is_active = models.BooleanField(default=True, verbose_name='Activa')

    def __str__(self):
        return self.name

    def get_image(self):
        if self.image:
            return '{}{}'.format(settings.MEDIA_URL, self.image)
        return '{}{}'.format(settings.STATIC_URL, 'img/logo.png')

    def toJSON(self):
        item = model_to_dict(
            self,
            exclude=['user_creation', 'user_updated', 'date_creation', 'date_updated'],
        )
        item['image'] = self.get_image()
        item['users_count'] = self.users.count()
        return item

    class Meta:
        verbose_name = 'Tienda'
        verbose_name_plural = 'Tiendas'
        ordering = ['name']


class User(AbstractUser):
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')
    first_name = models.CharField('first name', max_length=150, blank=True)
    image = models.ImageField(upload_to='users/%y/%m/%d', null=True, blank=True)
    organizations = models.ManyToManyField(
        Organization,
        related_name='users',
        blank=True,
        verbose_name='Tiendas disponibles',
    )
    current_organization = models.ForeignKey(
        Organization,
        on_delete=models.SET_NULL,
        related_name='current_users',
        null=True,
        blank=True,
        verbose_name='Tienda activa',
    )

    def get_image(self):
        if self.image:
            return '{}{}'.format(settings.MEDIA_URL, self.image)
        return '{}{}'.format(settings.STATIC_URL, 'img/imagen.png')

    def get_accessible_organizations(self):
        queryset = Organization.objects.filter(is_active=True)
        if self.is_superuser:
            return queryset.order_by('name')
        return queryset.filter(pk__in=self.organizations.values_list('pk', flat=True)).order_by('name')

    def get_manageable_organizations(self):
        return self.get_accessible_organizations()

    def get_role_names(self):
        role_names = list(self.groups.values_list('name', flat=True))
        if self.is_superuser and ROLE_SUPER_ADMIN not in role_names:
            role_names.append(ROLE_SUPER_ADMIN)
        return sort_role_names(role_names)

    def get_primary_role(self):
        role_names = self.get_role_names()
        return role_names[0] if role_names else None

    def get_role_priority(self):
        return get_user_role_priority(self)

    def get_assignable_role_names(self):
        return get_assignable_role_names(self)

    def can_manage_users(self):
        return self.is_superuser or bool(self.get_assignable_role_names())

    def can_manage_user(self, user):
        return can_manage_user(self, user)

    def get_manageable_users_queryset(self):
        queryset = type(self).objects.all().prefetch_related('groups', 'organizations').order_by('id')
        if self.is_superuser:
            return queryset

        if not self.can_manage_users():
            return queryset.none()

        organization_ids = self.get_manageable_organizations().values_list('pk', flat=True)
        scoped_queryset = queryset.filter(organizations__in=organization_ids, is_superuser=False).distinct()
        manageable_ids = [user.pk for user in scoped_queryset if self.can_manage_user(user)]
        return scoped_queryset.filter(pk__in=manageable_ids)

    def get_current_organization_object(self):
        if not self.current_organization_id:
            return None
        return Organization.objects.filter(pk=self.current_organization_id, is_active=True).first()

    def has_organization_access(self, organization):
        if organization is None:
            return False
        if self.is_superuser:
            return True
        return self.organizations.filter(pk=organization.pk).exists()

    @transaction.atomic
    def ensure_default_organization(self):
        if not self.pk:
            return None

        organizations = self.get_accessible_organizations()
        if organizations.exists():
            organization = organizations.filter(pk=self.current_organization_id).first() or organizations.first()
            if self.current_organization_id != organization.id:
                self.current_organization = organization
                self.save(update_fields=['current_organization'])
            return organization

        organization = Organization.objects.create(
            name='Tienda Principal {}'.format(self.username or self.pk),
            code='STORE-{}'.format(self.pk),
        )
        self.organizations.add(organization)
        self.current_organization = organization
        self.save(update_fields=['current_organization'])
        return organization

    def get_current_organization(self):
        if not self.is_authenticated:
            return None
        current_organization = self.get_current_organization_object()
        if current_organization and self.has_organization_access(current_organization):
            return current_organization
        return self.ensure_default_organization()

    def set_current_organization(self, organization):
        if organization is None or not self.has_organization_access(organization):
            return False
        if self.current_organization_id != organization.id:
            self.current_organization = organization
            self.save(update_fields=['current_organization'])
        return True

    def get_group_session(self):
        return self.get_current_organization()

    def toJSON(self):
        item = model_to_dict(self, exclude=['password', 'user_permissions', 'last_login'])
        current_organization = self.get_current_organization()
        if self.last_login:
            item['last_login'] = self.last_login.strftime('%Y-%m-%d')
        item['date_joined'] = self.date_joined.strftime('%Y-%m-%d')
        item['image'] = self.get_image()
        item['full_name'] = self.get_full_name()
        item['groups'] = [{'id': g.id, 'name': g.name} for g in self.groups.all()]
        item['roles'] = self.get_role_names()
        item['primary_role'] = self.get_primary_role()
        item['organizations'] = [organization.toJSON() for organization in self.get_accessible_organizations()]
        item['current_organization'] = current_organization.toJSON() if current_organization else None
        return item
