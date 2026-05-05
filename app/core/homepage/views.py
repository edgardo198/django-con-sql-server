from django.shortcuts import redirect
from django.views.generic import TemplateView

class IndexView(TemplateView):
    template_name = 'index.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('erp:dashboard')
        return super().dispatch(request, *args, **kwargs)
