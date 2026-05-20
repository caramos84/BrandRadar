# BrandRadar — UI Base: Login, Signup & Forgot Password

## Purpose

This document defines the visual, functional and technical baseline for the BrandRadar Login and Signup screens.

These screens are the first access layer of the product. Their role is not to show the full platform yet, but to establish the product identity, visual tone and entry experience.

BrandRadar should feel like a visual analysis observatory for brand assets, not like a generic SaaS login, DAM, file manager or corporate dashboard.

---

## Product Name

Use only:

**BrandRadar**

Do not use:

- GraphNebula
- GraphRadar
- StudioBlank
- Asset Archive
- DesignOps Visual Catalog

---

## Screens in Scope

Current scope includes only:

1. Login
2. Signup

Out of scope for this stage:

- Backend authentication
- Database integration
- JWT/session handling
- Dashboard
- Upload flow
- Brand spaces
- Asset analysis views
- Reports
- User management
- Role-based permissions

---

## Navigation

The interface uses local client-side navigation between:

- `LOGIN`
- `SIGN UP`

Default screen:

- Login

No routing library is required at this stage unless the app architecture later demands it.

---

## Visual Direction

The current visual language is:

- Minimalist
- Brutalist
- Black and white
- Editorial
- Analytical
- Corporate enough for internal demo
- Distinct from generic SaaS UI

The layout should preserve:

- Black outer background
- Large white central panel
- Strong typography
- Sparse interface
- Precise spacing
- Radar-inspired identity
- Clean form structure

Avoid:

- Colorful gradients
- Friendly rounded SaaS cards
- Decorative dashboards
- Overly soft UI
- Stock startup aesthetics

---

## Typography

BrandRadar uses two typographic roles.

### Helvetica / System Helvetica

Used for:

- BrandRadar wordmark
- Large headlines
- Navigation labels
- Primary buttons
- Strong identity moments

Suggested stack:

```css
font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
```

### IBM Plex Sans

Used for:

- Form labels
- Inputs
- Helper text
- Microcopy
- Interface text
- Future data-heavy UI

Suggested stack:

```css
font-family: "IBM Plex Sans", Inter, "Segoe UI", sans-serif;
```

If IBM Plex Sans is not installed locally, it may be imported safely via CSS.

## Login Screen

### Required content

Brand:

- BrandRadar logo / wordmark

Top navigation:

- SIGN UP
- LOGIN

Headline:

/* UNDERSTANDING YOUR BRAND UNIVERSE */

Form intro:

/* Welcome back */

Fields:

- EMAIL
- PASSWORD

Helper link:

/* FORGOT YOUR PASSWORD? */

Primary button:

/* ACCESS PANEL */

### UX notes

The login form should feel precise and intentional.

The form should not overpower the headline, but it must have enough presence to feel usable.

Input borders should be clear. Spacing should be generous enough for a premium analytical tool.

---

## Signup Screen

### Required content

Brand:

- BrandRadar logo / wordmark

Top navigation:

- SIGN UP
- LOGIN

Form intro or heading:

/* Welcome! */

Fields:

- NAME
- EMAIL
- PASSWORD
- CONFIRM PASSWORD
- WORK ROLE

Primary button:

/* CREATE ACCESS */

Alternative allowed button text:

/* SUBMIT */

Preferred current choice:

/* CREATE ACCESS */

### UX notes

The signup form should remain clean even with five fields.

WORK ROLE is a lightweight descriptor for now. It does not imply a full permission system yet.

No real role-based access should be implemented in this stage.

---
## Forgot Password Screen

### Required content

Brand:

- BrandRadar logo / wordmark

Headline:

```text
Reset access
```
Subtext:

```text
Enter your email and we’ll prepare a recovery link.
```

Fields:

- EMAIL

Primary button:

- SEND RECOVERY LINK

Secondary action:

- Back to login

### UX notes

This screen completes the access flow visually.

At this stage it is UI-only. It must not send real emails, generate reset tokens, or connect to backend services.

After submit, the screen may show a local confirmation message:

```text
If this email exists, a recovery link will be sent.
```

---

## Dark Mode Toggle

The visual toggle may remain present.

Current label:

/* DARK MODE */

At this stage, it may work as a local visual toggle only.

Out of scope:

- Theme persistence
- User preference saving
- Backend theme sync

---

## Technical Rules

All frontend files for this module must live inside:

/* /frontend */

Do not create frontend application files in the repository root.

Allowed frontend locations:

/* /frontend/index.html
/frontend/package.json
/frontend/tsconfig.json
/frontend/vite.config.ts
/frontend/src/ */

Do not create or modify these in root:

/* /index.html
/package.json
/src/
 /tsconfig.json
/vite.config.ts */

---

## Current Technical Stack

Frontend:

- React
- Vite
- TypeScript
- CSS

Do not introduce unnecessary dependencies for this stage.

Avoid:

- UI frameworks
- Auth libraries
- Routing libraries
- State management libraries
- Backend API calls

---

## Acceptance Criteria

The Login / Signup module is considered stable when:

- npm run dev works from /frontend
- Login appears by default
- User can switch to Signup and back
- Login contains EMAIL and PASSWORD
- Signup contains NAME, EMAIL, PASSWORD, CONFIRM PASSWORD and WORK ROLE
- BrandRadar name appears correctly
- No references to old project names exist
- No console errors appear
- Visual identity remains black/white, minimal and brutalist
- Frontend files are contained inside /frontend
- No backend/auth/database logic is introduced

## Next Stage

After this UI module is stable, the next planned stage is:

- Minimal backend authentication model
- users table
- Signup endpoint
- Login endpoint
- Frontend/backend connection

Suggested future backend fields:

/* users
- idnpm run dev
- name
- email
- password_hash
- work_role
- created_at
- updated_at */

This is not part of the current Login/Signup UI task.