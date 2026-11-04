from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    DeleteView,
)
from django.db.models import Prefetch
from apps.trips.models import Trip
from apps.trips.models.trip_image import TripImage
from apps.core.mixins import PermissionRequiredMixin
# Create your views here.


class TripListView(ListView):
    model = Trip
    template_name = "trips/trip_list.html"
    context_object_name = "trips"

    def get_queryset(self):
        return (
            Trip.objects.prefetch_related(
                Prefetch(
                    "images",
                    queryset=TripImage.objects.filter(is_cover=True),
                    to_attr="cover_images",
                )
            )
        )


class TripDetailView(DetailView):
    model = Trip
    template_name = "trips/trip_detail.html"
    context_object_name = "trip"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .prefetch_related(
                Prefetch(
                    "images",
                    queryset=TripImage.objects.order_by(
                        "-is_cover",
                        "sort_order",
                        "id",
                    ),
                    to_attr="detail_images",
                )
            )
        )


class TripCreateView(PermissionRequiredMixin, CreateView):
    model = Trip
    fields = "__all__"
    template_name = "trips/trip_form.html"
    success_url = reverse_lazy("trips:list")


class TripUpdateView(PermissionRequiredMixin, UpdateView):
    model = Trip
    fields = "__all__"
    template_name = "trips/trip_form.html"
    slug_field = "slug"
    slug_url_kwarg = "slug"
    success_url = reverse_lazy("trips:list")


class TripDeleteView(DeleteView):
    model = Trip
    template_name = "trips/trip_confirm_delete.html"
    slug_field = "slug"
    slug_url_kwarg = "slug"
    success_url = reverse_lazy("trips:list")