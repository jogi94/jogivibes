# Jogi Vibes UX/UI Architecture

## Status
Approved — Step 2B.

## Frontend Presentation Architecture
Customer-facing templates use one shared project-level directory: `apps/templates/`.

Pages extend `base.html`. Reusable presentation elements use Django `include` components. Business logic remains in views/services/use-cases.

Navigation uses `apps/core/navigation.py` and `apps/core/context_processors.py`. No third-party navigation/menu package is installed.

## Principles
- Customer-first, mobile-first experience.
- Modern Himalayan Adventure visual direction.
- Django server-rendered templates with Unpoly progressive enhancement.
- Server remains authoritative for availability, pricing, booking and validation.
- Thin views; existing service/use-case layer for business logic.
- No SPA framework.
- No new database models or fields for the Home Page.
- Do not invent trip data, pricing, availability, testimonials, certifications or safety claims.

## Customer Journey
Discover Trip → Trip Detail → Select Departure → Select Package → Traveler Information → Booking → Payment → Confirmation.

## Architecture Guardrail
Any persistent content system, new taxonomy, new backend workflow/API, or other capability outside existing architecture requires `ARCHITECTURE CHANGE REQUIRED`.
