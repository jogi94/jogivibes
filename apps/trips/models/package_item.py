from django.db import models

from apps.core.models import TrackedModel
from apps.trips.models.package import Package


class PackageItem(TrackedModel):
    package = models.ForeignKey(Package, on_delete=models.CASCADE, related_name="items")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    sort_order = models.PositiveSmallIntegerField(default=0)
    is_included = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order", "id"]
        constraints = [models.UniqueConstraint(fields=["package", "sort_order"], name="unique_package_item_order")]
        indexes = [models.Index(fields=["package", "sort_order"], name="package_item_order_idx")]

    def __str__(self):
        return f"{self.package.name} - {self.name}"