from django.conf import settings
from django.http import Http404


class PublicEnquiryOnlyMiddleware:
    """Expose only the lead-generation pages to anonymous visitors."""

    public_paths = {
        "/leads/enquiry/",
        "/leads/enquiry/success/",
    }

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
            settings.PUBLIC_ENQUIRY_ONLY
            and not request.user.is_authenticated
            and request.path not in self.public_paths
        ):
            raise Http404("Page not found.")

        return self.get_response(request)
