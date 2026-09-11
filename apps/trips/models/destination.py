from django.db import models

from apps.core.models import TrackedModel


class Destination(TrackedModel):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=280, unique=True)
    region = models.CharField(max_length=150, blank=True)
    country = models.CharField(max_length=150)
    state = models.CharField(max_length=150, blank=True)
    city = models.CharField(max_length=150, blank=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name