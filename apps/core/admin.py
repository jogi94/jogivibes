from django.contrib import admin

# Register your models here.


class TrackedModelAdminMixin:
    """Populate audit actors for admin-managed TrackedModel records."""

    def save_model(self, request, obj, form, change):
        if hasattr(obj, "created_by_id") and not change:
            obj.created_by = request.user

        if hasattr(obj, "modified_by_id"):
            obj.modified_by = request.user

        super().save_model(request, obj, form, change)
