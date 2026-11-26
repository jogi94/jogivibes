from django.urls import path
from apps.leads.views import (LeadListView, LeadDetailView,
                              PublicEnquiryView,
                              PublicEnquirySuccessView,
                              LeadInteractionCreateView,
                              LeadStatusUpdateView)


app_name = "leads"


urlpatterns = [
    path("", LeadListView.as_view(), name="lead_list"),
    path("<int:pk>/", LeadDetailView.as_view(), name="lead_detail"),
    path("<int:pk>/interactions/", LeadInteractionCreateView.as_view(), name="interaction_create"),
    # Public enquiry
    path("enquiry/", PublicEnquiryView.as_view(), name="leads_enquiry"),
    path("enquiry/success/", PublicEnquirySuccessView.as_view(), name="enquiry_success"),
    path("<int:pk>/status/", LeadStatusUpdateView.as_view(), name="status_update"),
]