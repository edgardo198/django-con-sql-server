import app.settings as settings
from django import forms
from django.contrib.auth import login, logout
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UsernameField
from django.contrib.auth.views import LoginView
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.views.generic import FormView, RedirectView


class UsernameOrEmailAuthenticationForm(AuthenticationForm):
    username = UsernameField(
        label='Usuario o correo',
        widget=forms.TextInput(attrs={'autofocus': True}),
    )

    def clean(self):
        username = self.cleaned_data.get('username')
        if username and '@' in username:
            user_model = get_user_model()
            user = user_model.objects.filter(email__iexact=username).order_by('pk').first()
            if user:
                self.cleaned_data['username'] = user.get_username()
        return super().clean()


class LoginFormView(LoginView):
    template_name = 'login.html'
    authentication_form = UsernameOrEmailAuthenticationForm

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect(settings.LOGIN_REDIRECT_URL)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Inicio de sesion'
        return context


class LoginFormView2(FormView):
    form_class = UsernameOrEmailAuthenticationForm
    template_name = 'login.html'
    success_url = settings.LOGIN_REDIRECT_URL

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return HttpResponseRedirect(self.success_url)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        login(self.request, form.get_user())
        return HttpResponseRedirect(self.success_url)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Iniciar sesion'
        return context


class LogoutRedirectView(RedirectView):
    pattern_name = 'login'

    def dispatch(self, request, *args, **kwargs):
        logout(request)
        return super().dispatch(request, *args, **kwargs)
