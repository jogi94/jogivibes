from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("leads", "0004_lead_phone_verification_and_otp"),
    ]

    operations = [
        migrations.AddField(
            model_name="leadphoneotp",
            name="lead",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="phone_otp_challenges",
                to="leads.lead",
            ),
        ),
    ]
