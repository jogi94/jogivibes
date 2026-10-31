from django.db import models


class TripType(models.TextChoices):
    YATRA = "YATRA", "Yatra"
    TREK = "TREK", "Trek"
    DARSHAN = "DARSHAN", "Darshan"
    BIKE_ROADTRIP = "BIKE_ROADTRIP", "Bike Roadtrip"
    FOREIGN_TRIP = "FOREIGN_TRIP", "Foreign Trip"
    FAMILY_HOLIDAYS = "FAMILY_HOLIDAYS", "Family Holidays"


class TripStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    PUBLISHED = "published", "Published"
    ARCHIVED = "archived", "Archived"


class TripDifficulty(models.TextChoices):
    EASY = "easy", "Easy"
    MODERATE = "moderate", "Moderate"
    HARD = "hard", "Hard"
    EXTREME = "extreme", "Extreme"


class Season(models.TextChoices):
    SPRING = "spring", "Spring"
    SUMMER = "summer", "Summer"
    MONSOON = "monsoon", "Monsoon"
    AUTUMN = "autumn", "Autumn"
    WINTER = "winter", "Winter"


class PricingType(models.TextChoices):
    STANDARD = "standard", "Standard"
    CUSTOM = "custom", "Custom"