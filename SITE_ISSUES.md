# Aluyè Naturals — Known Site Issues
Last updated: 2026-07-05

Status legend: 🔴 Open · ✅ Resolved & deployed · ⚪ Checked, not reproducible · — Skipped by decision

## SESSION: Admin/store functionality audit (stock, subscribers, messaging, currency, shipping)

27. ✅ Footer newsletter signup form (highest-traffic subscribe form, present on every page) was completely fake — showed a hardcoded "Thank you" message and never called the backend. Rebuilt to call `/api/subscribe` for real, with validation, duplicate detection, and success/error states.
28. ✅ Stock changes (orders, cancellations, manual admin edits) were never logged anywhere for audit purposes. Added a `stock_log` table + admin view at Products → Stock log.
29. ✅ Admin's "Send welcome email" toggle and custom subject/body fields in Global Settings → Newsletter did nothing at all — the welcome email function ignored all three. Now wired up and respected.
30. ✅ No email was ever sent when an order was marked Shipped or Delivered. Added admin-configurable automated emails for both, plus a customer inquiry auto-response on contact form submission (Global Settings → Automated Messages).
31. ✅ Abandoned cart table existed but nothing ever populated it. Added real capture (on checkout email entry) + an APScheduler background job that sends a configurable reminder email and marks carts as reminded. Disabled by default — admin must opt in (Global Settings → Automated Messages).
32. ✅ Currency selector only converted displayed prices; the admin's "Default currency" setting was ignored (always defaulted to CAD) and there was no location-based suggestion. Wired the admin setting as the true default and added a best-effort geo-IP suggestion for first-time visitors (falls back silently if the lookup fails). CAD remains the only currency PayPal actually charges in, by design.
33. 🔴 Google Maps distance-based shipping — built to spec (admin-configurable base fee, cost/km, max distance, free-delivery threshold, store origin) with automatic fallback to the existing zone system, but **not yet tested against a real Google Maps API key** (none provided this session). Zone-based shipping remains fully active until a key is added.

## SESSION: Full end-to-end site + admin audit (pre-launch)

34. ✅ Duplicate "Payment Methods" admin page removed — PayPal, Stripe, Flutterwave and Paystack are each now configured in exactly one place (Global Settings → Integrations). The old page saved to a settings bucket ("payments") that nothing else in the codebase ever read — so credentials entered there were silently inert. Confirmed no real credentials had ever been saved there before removing it.
35. ✅ Product detail page threw `trackRecentlyViewed is not defined` on every single load (uncaught JS error, visible in console on every product page). Caused by an inline script calling an `app.js` function before the deferred script had executed. Fixed by deferring the call to `DOMContentLoaded`.
36. ⚪ Full site + admin crawl (30+ public routes, 23 admin routes, 651 internal links/images) — zero broken links, zero missing images, zero HTTP 500s, zero console/JS errors after the fix above.
37. ⚪ Admin CRUD spot-checked across Products, Discounts, Shipping Zones, Blog/Journal, Notifications, and Settings (General/SEO/Social/Automated Messages) — all create/edit/delete/save operations persist correctly.
38. — No FAQ page exists anywhere on the site (not a bug — informational). No dedicated "Customers" or "Categories" admin modules exist either; customer data lives on Orders/Subscribers, categories are edited per-product. "Reports" maps to the existing Analytics page + CSV export.

## CRITICAL

1. ✅ Meta description showing broken "trans-" template variables — fixed.
2. ⚪ Cart drawer X button not closing the cart — tested repeatedly (desktop + mobile), works correctly.
3. ✅ Site not responsive on mobile — audited and fixed across the full site and admin (product grids, carousels, badge overlap, admin dashboard/notifications/tables). Verified zero horizontal overflow across breakpoints.
4. ✅ Stock levels not reducing after an order is placed — fixed. Deducts on order placement, restores on cancellation. Verified end-to-end with real test orders (20→17→20 stock).
5. ✅ Discount popup not capturing emails correctly — fixed. Real-time validation, duplicate detection, and the actual RITUAL10 code now displays on success.

## HIGH PRIORITY

6. ✅ WhatsApp floating button — fully removed (template, CSS, JS).
7. ✅ Address showing full street address — now shows "Toronto, Ontario, Canada" everywhere.
8. ✅ Welcome subscription email never sending — built and wired up. (Root cause found later: `Flask-Mail` wasn't even installed in the environment — see #17.)
9. ✅ Social media links not connected to real accounts — fixed.
10. ✅ Google showing a stale/wrong SEO snippet ("Welcome to WordPress...") — the live code never contained this; it's a stale cached Google index from before this site existed at the domain. Fixed the admin SEO tab (was entirely non-functional) so Meta Title/Description, Search Console verification, GA, and Facebook Pixel now actually work. Getting Google to drop the stale snippet requires verifying + requesting re-indexing in Search Console (your action, instructions provided).

## MEDIUM PRIORITY

11. ⚪ Product images displaying in circular format — not reproducible; all product images already square/rectangular. Only the intentional homepage category nav circles are round.
12. ✅ Maintenance mode not usable — rebuilt with full branding, email capture, and a `?preview=aluye2026` team bypass.
13. — No "coming soon" page — deliberately skipped; the store is live and taking real orders.
14. ⚪ Footer accordion on mobile — tested, expands/collapses correctly.
15. ✅ Service worker intercepting admin/API routes — fixed.
16. ✅ Admin settings tab reset to General after saving, making saves look broken — fixed (redirect now preserves the tab).
17. ✅ Admin-configured SMTP settings were saved but never actually used — centralized into one mail helper that respects them.
18. ✅ `Flask-Mail` package was missing from the environment entirely — every email send was silently failing or crashing. Installed and hardened against this recurring.
19. ✅ Admin SEO tab (meta title/description, Search Console verification, Google Analytics, Facebook Pixel) did nothing at all when saved — all four now wired up and tested.
20. 🔴 PayPal checkout — built to PayPal's real Orders API v2 spec (create/capture, admin config, hidden until configured, secrets never exposed to the frontend), but **not yet tested against a real PayPal sandbox or live account**. Needs real credentials before customers rely on it.

## LOW PRIORITY

21. ✅ Currency selector in footer — CAD is now the true base currency (was previously backwards, converting CAD from USD).
22. ⚪ Admin sidebar placeholder links — none found.
23. ⚪ Missing OG image for social sharing — not reproducible; every page has a default OG image fallback.
24. 🔴 ~16 product photos are still JPG/PNG rather than WebP — real but low-priority optimization opportunity.
25. ✅ A legacy "Payment Methods" admin page duplicated the real PayPal/Stripe/Flutterwave/Paystack settings now living in Global Settings → Integrations — removed entirely (route, nav item, template, and dead settings bucket). See full-audit session below.
26. 🔴 Tax rate is configurable in admin but not actually applied to checkout totals.

## RESOLVED (cumulative, verified across sessions)

- Announcement bar ticker, breadcrumbs, unified admin panel layout
- Broken meta description `trans-` placeholders
- Real Instagram/TikTok links connected
- Service worker no longer intercepts `/admin` or API routes
- Full mobile responsiveness (frontend + admin)
- Stock deduction/restoration
- WhatsApp removed
- Address, exit-popup, welcome email, admin settings save bugs, SEO admin tab
- PayPal, zone-based shipping, CAD currency, admin notifications detail/archive/delete, admin dark mode — all built and tested this session (PayPal pending real-account testing per above)
