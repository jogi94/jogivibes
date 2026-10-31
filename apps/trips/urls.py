from django.urls import path
from apps.trips.views import (
    TripListView,
    TripDetailView,
    TripCreateView,
    TripUpdateView,
    TripDeleteView,
)


app_name = "trips"


urlpatterns = [
    # Keep existing URLs here
    path("", TripListView.as_view(), name="list"),
    path("create/", TripCreateView.as_view(), name="trip_create"),
    path("<slug:slug>/", TripDetailView.as_view(), name="trip_detail"),
    path("<slug:slug>/edit/", TripUpdateView.as_view(), name="trip_update"),
    path("<slug:slug>/delete/", TripDeleteView.as_view(), name="trip_delete"),

]
