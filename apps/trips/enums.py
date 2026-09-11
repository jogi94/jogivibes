from django.db import models


class TripType(models.TextChoices):
    TREK = "trek", "Trek"
    EXPEDITION = "expedition", "Expedition"
    BIKE_ROADTRIP = "bike_roadtrip", "Bike Roadtrip"
    FOREIGN_TRIP = "foreign_trip", "Foreign Trip"
    FAMILY_HOLIDAYS = "family_holidays", "Family Holidays"


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