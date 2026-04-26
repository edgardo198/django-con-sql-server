from django import forms
from django.contrib.auth.models import Group
from django.forms import ModelForm, PasswordInput, Select, SelectMultiple, TextInput

from app.core.user.access import ensure_role_groups
from app.core.user.models import Organization, User


class OrganizationForm(ModelForm):
    class Meta:
        model = Organization
        fields = ('name', 'code', 'rtn', 'phone', 'email', 'address', 'image', 'is_active')
        widgets = {
            'name': TextInput(attrs={'placeholder': 'Ingrese el nombre de la tienda', 'autofocus': True}),
            'code': TextInput(attrs={'placeholder': 'Codigo interno'}),
            'rtn': TextInput(attrs={'placeholder': 'RTN'}),
            'phone': TextInput(attrs={'placeholder': 'Telefono'}),
            'email': TextInput(attrs={'placeholder': 'Correo'}),
            'address': TextInput(attrs={'placeholder': 'Direccion'}),
        }

    def save(self, commit=True):
        data = {}
        try:
            if self.is_valid():
                self.instance.full_clean()
                super().save(commit=commit)
            else:
                data['error'] = self.errors
        except Exception as e:
            data['error'] = str(e)
        return data


class UserForm(ModelForm):
    password = forms.CharField(
        label='Password',
        required=False,
        widget=PasswordInput(
            attrs={
                'placeholder': 'Ingrese una nueva password',
                'autocomplete': 'new-password',
            }
        ),
        help_text='En edicion, deje este campo vacio para conservar la password actual.',
    )

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        ensure_role_groups()
        super().__init__(*args, **kwargs)

        request_user = None
        if self.request and self.request.user.is_authenticated:
            request_user = self.request.user

        self.fields['first_name'].widget.attrs['autofocus'] = True
        self.fields['groups'].queryset = Group.objects.none()
        self.fields['organizations'].queryset = Organization.objects.none()
        self.fields['current_organization'].queryset = Organization.objects.none()

        if self.instance and self.instance.pk:
            self.fields['password'].widget.attrs['placeholder'] = 'Deje vacio para mantener la password actual'
            self.fields['password'].widget.attrs['autocomplete'] = 'new-password'

        if request_user:
            if request_user.is_superuser:
                allowed_group_names = request_user.get_assignable_role_names()
                organization_ids = set(Organization.objects.filter(is_active=True).values_list('pk', flat=True))
            elif self.instance.pk and request_user.pk == self.instance.pk:
                allowed_group_names = list(self.instance.groups.values_list('name', flat=True))
                organization_ids = set(request_user.get_accessible_organizations().values_list('pk', flat=True))
            else:
                allowed_group_names = request_user.get_assignable_role_names()
                organization_ids = set(request_user.get_manageable_organizations().values_list('pk', flat=True))
        else:
            allowed_group_names = list(Group.objects.values_list('name', flat=True))
            organization_ids = set(Organization.objects.filter(is_active=True).values_list('pk', flat=True))

        if self.instance.pk:
            organization_ids.update(self.instance.organizations.values_list('pk', flat=True))
            if self.instance.current_organization_id:
                organization_ids.add(self.instance.current_organization_id)

        self.fields['groups'].queryset = Group.objects.filter(name__in=allowed_group_names).order_by('name')
        organization_queryset = Organization.objects.filter(pk__in=organization_ids).order_by('name')
        self.fields['organizations'].queryset = organization_queryset
        self.fields['current_organization'].queryset = organization_queryset

    class Meta:
        model = User
        fields = (
            'first_name',
            'last_name',
            'email',
            'username',
            'password',
            'image',
            'groups',
            'organizations',
            'current_organization',
        )
        widgets = {
            'first_name': TextInput(attrs={'placeholder': 'Ingrese sus nombres'}),
            'last_name': TextInput(attrs={'placeholder': 'Ingrese sus apellidos'}),
            'email': TextInput(attrs={'placeholder': 'Ingrese su email'}),
            'username': TextInput(attrs={'placeholder': 'Ingrese su username'}),
            'image': forms.ClearableFileInput(attrs={'accept': 'image/*', 'capture': 'user'}),
            'groups': SelectMultiple(
                attrs={
                    'class': 'form-control select2',
                    'style': 'width: 100%',
                    'multiple': 'multiple',
                }
            ),
            'organizations': SelectMultiple(
                attrs={
                    'class': 'form-control select2',
                    'style': 'width: 100%',
                    'multiple': 'multiple',
                }
            ),
            'current_organization': Select(
                attrs={
                    'class': 'form-control select2',
                    'style': 'width: 100%',
                }
            ),
        }

    def clean(self):
        cleaned = super().clean()
        organizations = cleaned.get('organizations')
        current_organization = cleaned.get('current_organization')
        password = cleaned.get('password')
        groups = cleaned.get('groups')
        username = cleaned.get('username')

        if username:
            duplicated_user = User.objects.filter(username=username)
            if self.instance.pk:
                duplicated_user = duplicated_user.exclude(pk=self.instance.pk)
            if duplicated_user.exists():
                self.add_error('username', 'Ya existe otro usuario con este username.')

        if self.instance.pk is None and not password:
            self.add_error('password', 'La password es obligatoria para crear usuarios.')

        if not groups:
            self.add_error('groups', 'Debe asignar al menos un rol al usuario.')

        if current_organization and organizations is not None and current_organization not in organizations:
            self.add_error('current_organization', 'La tienda activa debe estar dentro de las tiendas disponibles.')

        if self.request and self.request.user.is_authenticated and not self.request.user.is_superuser:
            request_user = self.request.user
            if self.instance.pk and request_user.pk != self.instance.pk and not request_user.can_manage_user(self.instance):
                self.add_error(None, 'No tiene permiso para modificar este usuario.')

            if self.instance.pk and request_user.pk == self.instance.pk:
                allowed_organizations = set(request_user.get_accessible_organizations().values_list('pk', flat=True))
                allowed_roles = set(self.instance.groups.values_list('name', flat=True))
            else:
                allowed_organizations = set(request_user.get_manageable_organizations().values_list('pk', flat=True))
                allowed_roles = set(request_user.get_assignable_role_names())

            selected_organizations = set(organizations.values_list('pk', flat=True)) if organizations is not None else set()
            if not selected_organizations.issubset(allowed_organizations):
                self.add_error('organizations', 'Solo puede asignar usuarios a tiendas que usted administra.')

            selected_roles = set(groups.values_list('name', flat=True)) if groups is not None else set()
            if not selected_roles.issubset(allowed_roles):
                self.add_error('groups', 'No tiene permiso para asignar uno o mas de los roles seleccionados.')

        return cleaned

    def save(self, commit=True):
        data = {}
        try:
            if self.is_valid():
                password = self.cleaned_data.get('password')
                existing_password = None
                if self.instance.pk:
                    existing_password = User.objects.only('password').get(pk=self.instance.pk).password

                user = super().save(commit=False)

                if password:
                    user.set_password(password)
                elif existing_password:
                    user.password = existing_password

                if commit:
                    user.save()
                    user.groups.set(self.cleaned_data['groups'])
                    user.organizations.set(self.cleaned_data['organizations'])

                    current_organization = self.cleaned_data.get('current_organization')
                    if current_organization is None:
                        current_organization = user.organizations.order_by('name').first()
                    user.current_organization = current_organization
                    user.save(update_fields=['current_organization'])
            else:
                data['error'] = self.errors
        except Exception as e:
            data['error'] = str(e)
        return data
