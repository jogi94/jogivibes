from django.urls import path
from apps.leads.views import LeadListView, LeadDetailView
from apps.leads.views import LeadInteractionCreateView


app_name = "leads"


urlpatterns = [
    path("", LeadListView.as_view(), name="lead_list"),
    path("<int:pk>/", LeadDetailView.as_view(), name="lead_detail"),
    path("<int:pk>/interactions/", LeadInteractionCreateView.as_view(), name="interaction-create"),
]