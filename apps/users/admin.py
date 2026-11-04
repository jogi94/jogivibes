
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser

    ordering = ("-created",)
    list_display = (
        "phone_number",
        "first_name",
        "last_name",
        "username",
        "phone_verified",
        "is_active",
        "is_staff",
        "is_superuser",
    )

    list_filter = (
        "phone_verified",
        "is_active",
        "is_staff",
        "is_superuser",
        "groups",
    )

    search_fields = (
        "phone_number",
        "first_name",
        "last_name",
        "username",
    )

    fieldsets = (
        (None, {"fields": ("phone_number", "password")}),
        (
            _("Personal information"),
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "username",
                    "phone_verified",
                )
            },
        ),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (
            _("Important dates"),
            {"fields": ("last_login", "created", "modified")},
        ),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "phone_number",
                    "first_name",
                    "last_name",
                    "username",
                    "password1",
                    "password2",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                ),
            },
        ),
    )
    readonly_fields = ("last_login", "created", "modified")
