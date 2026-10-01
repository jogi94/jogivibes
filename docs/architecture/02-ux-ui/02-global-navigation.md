# Jogi Vibes Global Navigation

## Status
Approved — Step 2B.

## Navigation Abstraction
- `apps/core/navigation.py` builds navigation from published trip data.
- `apps/core/context_processors.py` exposes it as `navigation`.
- `apps/templates/components/navigation/navbar.html` renders desktop navigation.
- `apps/templates/components/navigation/mobile_menu.html` renders mobile navigation.
- No third-party navigation/menu package is installed.

## Navigation
Trips → Treks, Expeditions, Road Trips, Family Holidays.
Seasonal Trips → Winter Holidays, Summer Holidays.
Utility → About, Safety, FAQ, Contact, WhatsApp.

Only categories/seasons represented by relevant published data are exposed.
