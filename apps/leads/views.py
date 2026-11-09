from datetime import date
from django.db.models import Q
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, FormView, TemplateView
from apps.trips.models import Trip
from apps.leads.models import Lead
from apps.leads.permissions import get_accessible_leads, get_accessible_lead
from django.core.exceptions import ValidationError
from django.urls import reverse, reverse_lazy
from apps.leads.forms import LeadInteractionForm, PublicEnquiryForm, LeadStatusForm
from apps.leads.services import record_lead_interaction, create_public_enquiry, change_lead_status



class LeadListView(LoginRequiredMixin, ListView):
    model = Lead
    template_name = "leads/lead_list.html"
    context_object_name = "leads"
    paginate_by = 25

    def get_queryset(self):
        queryset = (
            get_accessible_leads(self.request.user)
            .select_related(
                "contact",
                "trip",
                "campaign",
                "assigned_to",
                "preferred_schedule",
            )
            .order_by("-created")
        )

        search = self.request.GET.get("q", "").strip()
        status = self.request.GET.get("status", "").strip()
        trip_id = self.request.GET.get("trip", "").strip()
        month = self.request.GET.get("month", "").strip()

        if search:
            queryset = queryset.filter(
                Q(contact__full_name__icontains=search)
                | Q(contact__phone_number__icontains=search)
                | Q(contact__email__icontains=search)
            )

        if status and status in dict(Lead._meta.get_field("status").choices):
            queryset = queryset.filter(status=status)

        if trip_id.isdigit():
            queryset = queryset.filter(trip_id=int(trip_id))

        if month:
            try:
                year, month_number = map(int, month.split("-"))
                date(year, month_number, 1)
                queryset = queryset.filter(
                    preferred_departure_month__year=year,
                    preferred_departure_month__month=month_number,
                )
            except (ValueError, TypeError):
                pass

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search_query"] = self.request.GET.get("q", "")
        context["selected_status"] = self.request.GET.get("status", "")
        context["selected_trip"] = self.request.GET.get("trip", "")
        context["selected_month"] = self.request.GET.get("month", "")
        context["status_choices"] = Lead._meta.get_field("status").choices
        context["trips"] = Trip.objects.order_by("name")
        return context


class LeadDetailView(LoginRequiredMixin, DetailView):
    model = Lead
    template_name = "leads/lead_detail.html"
    context_object_name = "lead"

    def get_object(self, queryset=None):
        return get_accessible_lead(
            self.request.user,
            self.kwargs["pk"],
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["interaction_form"] = LeadInteractionForm()
        context["status_form"] = LeadStatusForm(initial={"status": self.object.status})
        context["interactions"] = self.object.interactions.select_related("created_by").order_by("-interaction_date")
        context["status_history"] = self.object.status_history.select_related("changed_by").order_by("-changed_at")
        return context



class LeadInteractionCreateView(LoginRequiredMixin, FormView):
    template_name = "leads/lead_detail.html"
    form_class = LeadInteractionForm

    def dispatch(self, request, *args, **kwargs):
        self.lead = get_accessible_lead(request.user, kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["lead"] = self.lead
        context["interaction_form"] = context["form"]
        context["status_form"] = LeadStatusForm(initial={"status": self.lead.status})
        context["interactions"] = self.lead.interactions.select_related("created_by").order_by("-interaction_date")
        context["status_history"] = self.lead.status_history.select_related("changed_by").order_by("-changed_at")
        return context

    def form_valid(self, form):
        try:
            record_lead_interaction(user=self.request.user, lead_id=self.lead.pk, **form.cleaned_data)
        except ValidationError as error:
            form.add_error(None, error)
            return self.form_invalid(form)
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("leads:lead_detail", kwargs={"pk": self.lead.pk})



class PublicEnquiryView(FormView):
    template_name = "leads/public_enquiry.html"
    form_class = PublicEnquiryForm
    success_url = reverse_lazy("leads:enquiry-success")

    def form_valid(self, form):
        create_public_enquiry(**form.cleaned_data)
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["light_navigation"] = True
        return context


class PublicEnquirySuccessView(TemplateView):
    template_name = "leads/enquiry_success.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["light_navigation"] = True
        return context


class LeadStatusUpdateView(LoginRequiredMixin, FormView):
    template_name = "leads/lead_detail.html"
    form_class = LeadStatusForm

    def dispatch(self, request, *args, **kwargs):
        self.lead = get_accessible_lead(request.user, kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        initial["status"] = self.lead.status
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["lead"] = self.lead
        context["status_form"] = context.get("form")
        context["interaction_form"] = LeadInteractionForm()
        context["interactions"] = self.lead.interactions.select_related("created_by").order_by("-interaction_date")
        context["status_history"] = self.lead.status_history.select_related("changed_by").order_by("-changed_at")
        return context

    def form_valid(self, form):
        try:
            change_lead_status(
                user=self.request.user,
                lead_id=self.lead.pk,
                new_status=form.cleaned_data["status"],
                reason=form.cleaned_data["reason"],
            )
        except ValidationError as error:
            form.add_error(None, error)
            return self.form_invalid(form)
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("leads:lead_detail", kwargs={"pk": self.lead.pk})
