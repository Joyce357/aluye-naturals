# Aluyè Naturals — Known Site Issues
Last updated: 2026-07-04

Status legend: 🔴 Open · 🟡 Fixed locally, not yet deployed · ✅ Resolved & deployed · ⚪ Checked, not reproducible

## CRITICAL

1. ✅ Meta description showing broken "trans-" template variables — fixed in `bce87a9`.
2. ⚪ Cart drawer X button not closing the cart — tested locally (desktop + mobile), the close button works correctly. If this is still seen on the live site, confirm the deployed commit includes `3476f64`/`ff375d5`/`bdc6498` (cart drawer fixes).
3. 🟡 Site not responsive on mobile — confirmed and fixed this session. Found and fixed three distinct bugs: (a) the `/shop` and homepage product grids forced a single column below 481px due to a conflicting CSS override; (b) the homepage's horizontal product carousels (Skin Care, Oil, Men, Hair, Beards, African Black Soap) were squished into 3 cramped equal-width columns instead of scrolling, because a global `.product-card{width:100%}` mobile rule overrode the carousel's intended `min-w-[78vw]`; (c) long product badges (e.g. "Daily Cleanser") visually ran underneath the wishlist heart icon on narrow cards. All three verified fixed via direct DOM measurement and screenshots.
4. 🔴 Stock levels not reducing after an order is placed — confirmed: `products.stock` is never decremented anywhere in checkout. Fix in progress (Task 8).
5. 🟡 Exit-intent discount popup — captured emails but had no client-side validation, no duplicate/error handling, and never displayed the actual code or sent a welcome email. Backend (`/api/subscribe`) rebuilt this session; popup UI/JS hardening in progress (Task 5).

## HIGH PRIORITY

6. 🟡 WhatsApp floating button — removed from the site (template, CSS, JS) earlier this session; not yet deployed.
7. 🟡 Address showing full street address instead of "Toronto, Ontario, Canada" — fixed this session (footer, contact page, DB setting); not yet deployed.
8. 🟡 Welcome subscription email never sending — `templates/emails/welcome.html` existed but nothing called it. Built `send_welcome_email()` and wired it into `/api/subscribe` this session.
9. ✅ Social media links not connected to real accounts — fixed in `bce87a9`/`ac67050`/`f8a2e88`.

## MEDIUM PRIORITY

10. ⚪ Product images displaying in circular format — checked every product image location (shop grid, product detail, cart drawer, search, admin), all already use square/rectangular `aspect-[4/5]` framing with `object-contain` and sharp corners. The only circular images anywhere are the homepage category nav circles, which are intentional and correctly left untouched.
11. ⚪ Maintenance mode not available — it already exists (`store_status` toggle in Admin → Site Settings → General), just wasn't being used. Rebuilt the branded maintenance page and added a `?preview=aluye2026` team-bypass this session.
12. — No "coming soon" page — deliberately out of scope for this pass (site is live and taking orders; team decided not to gate it behind a coming-soon page).
13. ⚪ Footer accordion on mobile — tested on a 390px viewport; expands/collapses correctly.
14. ✅ Service worker intercepting admin/API routes — fixed in `51ab1b0`.

## LOW PRIORITY

15. 🔴 Currency selector in footer — present in the DOM but not yet verified against live exchange behavior; needs a follow-up pass.
16. ⚪ Admin sidebar placeholder links — checked `admin/base.html`, no placeholder (`href="#"`) links found; likely fixed in `7ec26c1`/`a583721`.
17. ⚪ Missing OG image for social sharing — checked `page_seo()`: every page falls back to a default hero image for `og:image` when a page-specific one isn't set. Not reproducible as stated.

## RESOLVED (verified this audit)

- Announcement bar ticker
- Breadcrumbs on inner pages
- Unified admin panel layout
- Broken meta description `trans-` placeholders
- Real Instagram/TikTok links connected
- Service worker no longer intercepts `/admin` or API routes
