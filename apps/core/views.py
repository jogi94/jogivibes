from django.views.generic import TemplateView
from apps.trips.selectors import get_homepage_carousel_slides


class HomeView(TemplateView):
    template_name = "core/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["carousel_slides"] = get_homepage_carousel_slides()
        return context