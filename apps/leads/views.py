from datetime import date
from django.db.models import Q
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, DetailView, FormView, TemplateView
from apps.trips.models import Trip
from apps.leads.models import Lead, Contact
from apps.leads.permissions import get_accessible_leads, get_accessible_lead
from django.core.exceptions import ValidationError
from django.urls import reverse, reverse_lazy
from django.shortcuts import redirect
from django.shortcuts import get_object_or_404
from apps.leads.forms import (
    LeadInteractionForm,
    PublicEnquiryForm,
    LeadStatusForm,
    LeadPhoneVerificationForm,
    EnquiryPhoneUpdateForm,
)
from apps.leads.services import (
    record_lead_interaction,
    create_public_enquiry,
    change_lead_status,
    send_lead_phone_otp,
    verify_lead_phone_otp,
)
from django.core.exceptions import ImproperlyConfigured



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



class PublicEnquiryView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    template_name = "leads/public_enquiry.html"
    form_class = PublicEnquiryForm
    success_url = reverse_lazy("leads:enquiry_success")

    def test_func(self):
        return self.request.user.is_staff

    def form_valid(self, form):
        if not form.cleaned_data.get("website"):
            form.cleaned_data.pop("website", None)
            lead = create_public_enquiry(
                user=self.request.user,
                **form.cleaned_data,
            )
            try:
                send_lead_phone_otp(
                    user=self.request.user,
                    lead=lead,
                    phone_number=lead.contact.phone_number,
                )
            except (ValidationError, ImproperlyConfigured):
                self.request.session["lead_otp_message"] = (
                    "The lead was saved as unverified, but we could not send an OTP. Use Resend code to try again."
                )
            return redirect("leads:enquiry_verify", pk=lead.pk)
        return super().form_valid(form)


class EnquiryPhoneVerificationView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    template_name = "leads/enquiry_verify_phone.html"
    form_class = LeadPhoneVerificationForm

    def test_func(self):
        self.lead = get_object_or_404(
            Lead.objects.select_related("contact"),
            pk=self.kwargs["pk"],
            created_by=self.request.user,
        )
        return self.request.user.is_staff and not self.lead.phone_verified

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["lead"] = self.lead
        context["otp_message"] = self.request.session.pop("lead_otp_message", "")
        return context

    def form_valid(self, form):
        if self.request.POST.get("action") == "resend":
            try:
                send_lead_phone_otp(
                    user=self.request.user,
                    lead=self.lead,
                    phone_number=self.lead.contact.phone_number,
                )
                self.request.session["lead_otp_message"] = "A new code was sent to the enquirer’s mobile."
            except (ValidationError, ImproperlyConfigured):
                self.request.session["lead_otp_message"] = "We could not send a new code. Check the SMS setup and try again."
            return redirect("leads:enquiry_verify", pk=self.lead.pk)

        code = form.cleaned_data["verification_code"].strip()
        if not code:
            form.add_error("verification_code", "Enter the code shared by the enquirer.")
            return self.form_invalid(form)
        try:
            valid = verify_lead_phone_otp(
                user=self.request.user,
                lead=self.lead,
                phone_number=self.lead.contact.phone_number,
                code=code,
            )
        except ValidationError as error:
            form.add_error(None, error)
            return self.form_invalid(form)
        if not valid:
            form.add_error("verification_code", "That code was not accepted. Try again or update the mobile number.")
            return self.form_invalid(form)

        self.lead.phone_verified = True
        self.lead.verified_phone_number = self.lead.contact.phone_number
        self.lead.modified_by = self.request.user
        self.lead.save(update_fields=["phone_verified", "verified_phone_number", "modified_by", "modified"])
        self.request.session["lead_enquiry_phone_verified"] = True
        return redirect("leads:enquiry_success")


class EnquiryPhoneUpdateView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    template_name = "leads/enquiry_edit_phone.html"
    form_class = EnquiryPhoneUpdateForm

    def test_func(self):
        self.lead = get_object_or_404(
            Lead.objects.select_related("contact"),
            pk=self.kwargs["pk"],
            created_by=self.request.user,
        )
        return self.request.user.is_staff and not self.lead.phone_verified

    def get_initial(self):
        return {"phone_number": self.lead.contact.phone_number}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["lead"] = self.lead
        return context

    def form_valid(self, form):
        phone_number = form.cleaned_data["phone_number"]
        if Contact.objects.filter(phone_number=phone_number).exclude(pk=self.lead.contact_id).exists():
            form.add_error("phone_number", "This number is already linked to another contact. Please confirm the enquirer’s number.")
            return self.form_invalid(form)
        self.lead.contact.phone_number = phone_number
        self.lead.contact.save()
        try:
            send_lead_phone_otp(
                user=self.request.user,
                lead=self.lead,
                phone_number=self.lead.contact.phone_number,
            )
            self.request.session["lead_otp_message"] = "A new code was sent to the updated mobile number."
        except (ValidationError, ImproperlyConfigured):
            self.request.session["lead_otp_message"] = "The number was updated, but we could not send a code. Use Resend code to try again."
        return redirect("leads:enquiry_verify", pk=self.lead.pk)


class PublicEnquirySuccessView(TemplateView):
    template_name = "leads/enquiry_success.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["light_navigation"] = True
        context["phone_verified"] = self.request.session.pop(
            "lead_enquiry_phone_verified", False
        )
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
