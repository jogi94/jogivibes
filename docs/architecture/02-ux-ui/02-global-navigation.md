# Jogi Vibes Global Navigation

## Status
Approved — Step 2B.

## Navigation Abstraction
Navigation is provided globally through:

- \`apps/core/navigation.py\` — builds the reusable navigation structure from published trip data.
- \`apps/core/context_processors.py\` — exposes the structure as the \`navigation\` template context.
- \`apps/templates/components/navigation/navbar.html\` — desktop presentation.
- \`apps/templates/components/navigation/mobile_menu.html\` — mobile presentation.

No third-party Django navigation/menu package is installed.

## Desktop Navigation
- JOGI VIBES
- Trips
  - Treks
  - Expeditions
  - Road Trips
  - Family Holidays
- Seasonal Trips
  - Winter Holidays
  - Summer Holidays
- About
- Safety
- FAQ
- Contact
- WhatsApp

## Mobile Navigation
Use the same navigation data structure as desktop with a compact accessible menu. Keep the primary customer paths discoverable and ensure the menu can be opened, closed and operated from the keyboard.

## Rules
- Category links only expose categories with relevant published trips.
- Seasonal links only expose seasons represented by relevant published trips.
- About, Safety, FAQ and Contact currently resolve to the approved Home Page sections until dedicated public pages exist.
- WhatsApp is an external action.
- Do not invent navigation destinations or business information.
- Major navigation is normal page navigation; Unpoly may progressively enhance applicable internal transitions.
