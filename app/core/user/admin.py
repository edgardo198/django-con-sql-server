from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from app.core.user.models import Organization, User


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'phone', 'email', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'code', 'rtn', 'email')
    ordering = ('name',)
    fields = ('name', 'code', 'rtn', 'phone', 'email', 'address', 'image', 'is_active')


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = (
        'username',
        'email',
        'first_name',
        'last_name',
        'roles_display',
        'current_organization',
        'is_superuser',
    )
    list_filter = ('is_superuser', 'is_staff', 'is_active', 'groups')
    search_fields = ('username', 'first_name', 'last_name', 'email')
    ordering = ('username',)
    filter_horizontal = ('groups', 'user_permissions', 'organizations')
    readonly_fields = ('last_login', 'date_joined')

    fieldsets = DjangoUserAdmin.fieldsets + (
        ('Multitienda', {
            'fields': ('organizations', 'current_organization', 'image'),
        }),
    )

    add_fieldsets = DjangoUserAdmin.add_fieldsets + (
        ('Multitienda', {
            'fields': ('organizations', 'current_organization', 'image'),
        }),
    )

    def roles_display(self, obj):
        return ', '.join(obj.get_role_names()) or 'Sin rol'

    roles_display.short_description = 'Roles'
