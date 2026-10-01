# Jogi Vibes UX/UI Architecture

## Status
Approved — Step 2B.

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

## Primary Public Screens
Home, Trips/Experiences, Trip Detail, Departure Selection, Package Selection, Booking, Confirmation, Inquiry, About, Safety, FAQ, Contact and legal pages where required.

## Home Page Sections
Hero, Featured Trips, Upcoming Departures, Why Jogi Vibes, Safety/Trust, Real Experiences, Seasonal Trips, How It Works, FAQ, Final CTA and Footer.

## Frontend Presentation Architecture
Use one shared project-level template directory at \`apps/templates/\` for customer-facing presentation.

\`\`\`text
apps/templates/
├── base.html
├── components/
│   ├── navigation/
│   ├── footer/
│   ├── trips/
│   └── ui/
├── core/
├── trips/
└── bookings/
\`\`\`

Pages extend \`base.html\`. Reusable presentation elements are rendered with Django {% include %} components. Business logic remains in views/services/use-cases and is passed to templates through context.

## Interaction Strategy
Use normal navigation for major page transitions. Use Unpoly fragments where content changes in place, including departure/package selection, validation and FAQ interactions. External WhatsApp actions remain normal external links.

## Accessibility
Use semantic headings and landmarks, keyboard-accessible controls, visible focus states, meaningful link labels, sufficient contrast, touch targets of approximately 44px, and reduced-motion support.

## Architecture Guardrail
Do not install a third-party navigation/menu package at this stage. The navigation is implemented through \`apps/core/navigation.py\` plus \`apps/core/context_processors.py\`.

Any persistent content system, new taxonomy, new backend workflow/API, or other capability outside existing architecture requires \`ARCHITECTURE CHANGE REQUIRED\` before implementation.
