from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin


class PermissionRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    required_permission = None
    staff_required = False
    owner_required = False

    def test_func(self):
        user = self.request.user

        # Staff access
        if self.staff_required and user.is_staff:
            return True

        # Django model permission
        if (
            self.required_permission
            and user.has_perm(self.required_permission)
        ):
            return True

        # Ownership check
        if self.owner_required:
            obj = self.get_object()
            return getattr(obj, "owner_id", None) == user.pk

        return False