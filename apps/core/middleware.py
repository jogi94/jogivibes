from django.conf import settings
from django.http import Http404


class PublicEnquiryOnlyMiddleware:
    """Expose enquiry entry, sign-in, and required static assets publicly."""

    public_paths = {
        "/leads/enquiry/",
        "/leads/enquiry/success/",
        "/accounts/login/",
    }

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
            settings.PUBLIC_ENQUIRY_ONLY
            and not request.user.is_authenticated
            and request.path not in self.public_paths
            and not request.path.startswith(settings.STATIC_URL)
        ):
            raise Http404("Page not found.")

        return self.get_response(request)
