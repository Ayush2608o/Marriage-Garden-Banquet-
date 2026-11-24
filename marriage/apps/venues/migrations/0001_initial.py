# Initial venue catalogue and wedding enquiry schema.

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Enquiry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120)),
                ("email", models.EmailField(max_length=254)),
                ("phone", models.CharField(max_length=24)),
                ("event_type", models.CharField(choices=[("wedding", "Wedding celebration"), ("reception", "Reception"), ("engagement", "Engagement"), ("other", "Another occasion")], default="wedding", max_length=20)),
                ("event_date", models.DateField(blank=True, null=True)),
                ("guest_count", models.PositiveIntegerField(blank=True, null=True)),
                ("message", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("contacted", models.BooleanField(default=False)),
            ],
            options={"verbose_name_plural": "enquiries", "ordering": ("-created_at",)},
        ),
        migrations.CreateModel(
            name="Venue",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120)),
                ("location", models.CharField(max_length=160)),
                ("description", models.TextField()),
                ("capacity", models.PositiveIntegerField(default=250)),
                ("starting_price", models.PositiveIntegerField(validators=[django.core.validators.MinValueValidator(0)])),
                ("image_url", models.URLField(blank=True)),
                ("featured", models.BooleanField(default=False)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ("-featured", "name")},
        ),
    ]
