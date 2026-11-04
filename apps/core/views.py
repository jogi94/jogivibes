from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from apps.trips.selectors import get_trip_categories


class HomeView(TemplateView):
    template_name = "core/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["carousel_slides"] = get_trip_categories()
        return context


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "layouts/dashboard.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        return super().dispatch(request, *args, **kwargs)