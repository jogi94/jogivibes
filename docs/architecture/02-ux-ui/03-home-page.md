# Jogi Vibes Home Page

## Status
Approved — Step 2B visual UI.

## Visual Direction
Modern Himalayan Adventure: authentic mountain imagery when approved assets are available, strong editorial typography, earthy natural palette, generous whitespace, and a premium but approachable feel.

## Design Tokens
- Primary: `#1F3A34`
- Primary Dark: `#142A25`
- Accent: `#C87941`
- Accent Dark: `#A85F2F`
- Sand: `#F2EDE4`
- Off White: `#FAF9F6`
- Surface: `#FFFFFF`
- Text: `#18201E`
- Muted: `#68716D`
- Border: `#DDE1DC`
- Success: `#2F6B4F`
- Warning: `#A66A20`
- Error: `#A64040`
- Font: Manrope, Arial/Helvetica fallback
- Desktop H1: 64px; H2: 44px; H3: 28px
- Mobile H1: 40px; H2: 32px; H3: 23px
- Section spacing: desktop 96px, tablet 72px, mobile 56px
- Desktop container: 1280px; large desktop: 1320px; mobile horizontal padding: 20px

## Hero
Headline: “Adventure Beyond the Ordinary”
Supporting copy: “Explore treks, expeditions and journeys with Jogi Vibes.”
Primary CTA: Explore Trips
Secondary CTA: Talk to Jogi Vibes

## Content
Featured Trips and Upcoming Departures are rendered from real published domain data. Empty states are used when no published records exist. No fabricated trip or commercial information is permitted.

## Trust
Why Jogi Vibes and Safety sections use factual, non-invented claims only.

## Seasonal
Winter Holidays and Summer Holidays are visual entry points and must not imply unavailable products.

## Responsive
Mobile-first; single-column mobile, two-column tablet where appropriate, three-column desktop trip cards, constrained large desktop layout.

## Accessibility
Semantic HTML, focus-visible states, accessible menu controls, keyboard-operable FAQ details, meaningful alt text for available images, adequate touch targets, and reduced-motion support.

## Implementation
Django templates under `apps/core/templates/core/`, app static assets under `apps/core/static/core/`, and Unpoly loaded for progressive enhancement. No database or backend architecture changes are required for this screen.

## Visual Asset Note
The repository does not currently contain an approved Home Page photography asset. The implementation therefore uses restrained visual placeholders/gradients rather than inventing or embedding unapproved imagery. Replace these with approved Jogi Vibes photography before final visual sign-off.
