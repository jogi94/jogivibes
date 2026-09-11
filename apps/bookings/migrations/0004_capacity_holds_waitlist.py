from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
from django.db.models import Q, F


class Migration(migrations.Migration):
    dependencies = [
        ("bookings", "0003_booking_capacity_quantity_tripschedule_capacity"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="booking",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"),
                    ("confirmed", "Confirmed"),
                    ("cancelled", "Cancelled"),
                ],
                db_index=True,
                default="confirmed",
                max_length=20,
            ),
        ),
        migrations.CreateModel(
            name="BookingHold",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created", models.DateTimeField(auto_now_add=True)),
                ("modified", models.DateTimeField(auto_now=True)),
                ("quantity", models.PositiveIntegerField()),
                ("status", models.CharField(choices=[("active", "Active"), ("converted", "Converted"), ("expired", "Expired"), ("released", "Released")], db_index=True, default="active", max_length=20)),
                ("expires_at", models.DateTimeField()),
                ("released_at", models.DateTimeField(blank=True, null=True)),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="booking_holds_created", to=settings.AUTH_USER_MODEL)),
                ("trip_schedule", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="holds", to="bookings.tripschedule")),
            ],
        ),
        migrations.CreateModel(
            name="CapacityOverride",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created", models.DateTimeField(auto_now_add=True)),
                ("modified", models.DateTimeField(auto_now=True)),
                ("previous_capacity", models.PositiveIntegerField()),
                ("new_capacity", models.PositiveIntegerField()),
                ("reason", models.TextField()),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="capacity_overrides_created", to=settings.AUTH_USER_MODEL)),
                ("trip_schedule", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="capacity_overrides", to="bookings.tripschedule")),
            ],
            options={"ordering": ["-created", "-id"]},
        ),
        migrations.CreateModel(
            name="WaitlistEntry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created", models.DateTimeField(auto_now_add=True)),
                ("modified", models.DateTimeField(auto_now=True)),
                ("requested_quantity", models.PositiveIntegerField()),
                ("status", models.CharField(choices=[("waiting", "Waiting"), ("cancelled", "Cancelled")], db_index=True, default="waiting", max_length=20)),
                ("cancelled_at", models.DateTimeField(blank=True, null=True)),
                ("traveler", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="waitlist_entries", to="bookings.traveler")),
                ("trip_schedule", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="waitlist_entries", to="bookings.tripschedule")),
            ],
        ),
        migrations.CreateModel(
            name="WaitlistOffer",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created", models.DateTimeField(auto_now_add=True)),
                ("modified", models.DateTimeField(auto_now=True)),
                ("offered_quantity", models.PositiveIntegerField()),
                ("status", models.CharField(choices=[("pending", "Pending"), ("accepted", "Accepted"), ("expired", "Expired"), ("declined", "Declined")], db_index=True, default="pending", max_length=20)),
                ("offered_at", models.DateTimeField()),
                ("expires_at", models.DateTimeField()),
                ("accepted_at", models.DateTimeField(blank=True, null=True)),
                ("declined_at", models.DateTimeField(blank=True, null=True)),
                ("waitlist_entry", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="offers", to="bookings.waitlistentry")),
            ],
        ),
        migrations.AddConstraint(
            model_name="tripschedule",
            constraint=models.CheckConstraint(condition=Q(("capacity__gt", 0)), name="trip_schedule_capacity_gt_zero"),
        ),
        migrations.AddConstraint(
            model_name="booking",
            constraint=models.CheckConstraint(condition=Q(("capacity_quantity__gt", 0)), name="booking_capacity_quantity_gt_zero"),
        ),
        migrations.AddConstraint(
            model_name="bookinghold",
            constraint=models.CheckConstraint(condition=Q(("quantity__gt", 0)), name="booking_hold_quantity_gt_zero"),
        ),
        migrations.AddConstraint(
            model_name="waitlistentry",
            constraint=models.CheckConstraint(condition=Q(("requested_quantity__gt", 0)), name="waitlist_entry_quantity_gt_zero"),
        ),
        migrations.AddConstraint(
            model_name="waitlistoffer",
            constraint=models.CheckConstraint(condition=Q(("offered_quantity__gt", 0)), name="wait_offer_quantity_gt_zero"),
        ),
        migrations.AddConstraint(
            model_name="waitlistoffer",
            constraint=models.UniqueConstraint(condition=Q(("status", "pending")), fields=("waitlist_entry",), name="unique_pending_wait_offer"),
        ),
        migrations.AddConstraint(
            model_name="capacityoverride",
            constraint=models.CheckConstraint(condition=Q(("previous_capacity__gt", 0)), name="capacity_override_previous_gt_zero"),
        ),
        migrations.AddConstraint(
            model_name="capacityoverride",
            constraint=models.CheckConstraint(condition=Q(("new_capacity__gt", 0)), name="capacity_override_new_gt_zero"),
        ),
        migrations.AddConstraint(
            model_name="capacityoverride",
            constraint=models.CheckConstraint(condition=~Q(("previous_capacity", F("new_capacity"))), name="capacity_override_capacity_changed"),
        ),
        migrations.AddIndex(model_name="booking", index=models.Index(fields=["trip_schedule", "status"], name="booking_schedule_status_idx")),
        migrations.AddIndex(model_name="bookinghold", index=models.Index(fields=["trip_schedule", "status"], name="hold_schedule_status_idx")),
        migrations.AddIndex(model_name="bookinghold", index=models.Index(fields=["trip_schedule", "status", "expires_at"], name="hold_schedule_status_exp_idx")),
        migrations.AddIndex(model_name="waitlistentry", index=models.Index(fields=["trip_schedule", "status", "created", "id"], name="wait_entry_fifo_idx")),
        migrations.AddIndex(model_name="waitlistoffer", index=models.Index(fields=["waitlist_entry", "status"], name="offer_entry_status_idx")),
        migrations.AddIndex(model_name="waitlistoffer", index=models.Index(fields=["status", "expires_at"], name="offer_status_exp_idx")),
        migrations.AddIndex(model_name="capacityoverride", index=models.Index(fields=["trip_schedule", "created"], name="capacity_override_schedule_idx")),
    ]
