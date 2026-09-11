from django.db import models
from django.contrib.auth.base_user import BaseUserManager, AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.db import models

# Create your models here.

class CustomUserManager(BaseUserManager):

    def create_user(self, phone_number, password=None, **extra_fields):

        if not phone_number:
            raise ValueError("Phone number is required")
        phone_number = self.normalize_phone_number(phone_number)
        user = self.model(phone_number=phone_number, **extra_fields)

        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()

        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if not extra_fields["is_staff"]:
            raise ValueError("Superuser must have is_staff=True")

        if not extra_fields["is_superuser"]:
            raise ValueError("Superuser must have is_superuser=True")

        user = self.create_user(
            phone_number,
            password=password,
            **extra_fields,
        )

        return user

    @staticmethod
    def normalize_phone_number(phone_number):
        # We should use a proper phone-number library here.
        return phone_number.strip()

class CustomUser(AbstractBaseUser, PermissionsMixin):
    phone_number = models.CharField(max_length=15, unique=True)
    phone_verified = models.BooleanField(default=False)
    first_name = models.CharField(max_length=150, null=True, blank=True)
    last_name = models.CharField(max_length=150, null=True, blank=True)
    username = models.CharField(max_length=150, unique=True, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    USERNAME_FIELD = "phone_number"
    REQUIRED_FIELDS = []
    objects = CustomUserManager()

    class Meta:
        db_table = "accounts_user"
        ordering = ["-created"]

        constraints = [
            models.CheckConstraint(
                condition=(
                    ~models.Q(first_name="")
                    | ~models.Q(last_name="")
                    | models.Q(username__isnull=False)
                ),
                name="user_has_name_or_username",
            ),
        ]

    def __str__(self):
        return (
            self.get_full_name()
            or self.username
            or self.phone_number
        )

    def get_full_name(self):
        return " ".join(part for part in [self.first_name, self.last_name] if part).strip()