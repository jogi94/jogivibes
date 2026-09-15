# Jogi Vibes — UX/UI Architecture

## Status

STEP 2B — Approved

## Scope

This document defines the reusable UX/UI architecture for the Jogi Vibes public website.

## Design Principles

- Mobile-first and responsive
- Modern Himalayan adventure visual direction
- Clear discovery-to-inquiry journey
- Reusable components and design tokens
- Strong visual hierarchy and readable typography
- Progressive enhancement compatible with Unpoly
- Accessible interactions and semantic HTML
- Thin Django views with reusable presentation components

## Core User Journey

Home → Discover Trips → Trip Detail → Inquiry / Booking → Communication

## Public Information Architecture

- Home
- Trips / Experiences
- Trip detail pages
- Search / Filters
- Community / WhatsApp

## Reusable UI System

The implementation should use shared components rather than page-specific duplication. Core reusable elements include:

- Global navigation
- Footer
- Buttons and CTA patterns
- Typography tokens
- Color and spacing tokens
- Cards
- Badges / status labels
- Form controls
- Responsive containers
- Section headers
- Trip metadata blocks

## Implementation Guidance

Use Django templates with reusable partials/components. Keep business logic out of templates and views. Use Tailwind CSS utilities and existing project conventions where available. Use Unpoly for progressive page interactions without requiring a full SPA architecture.
