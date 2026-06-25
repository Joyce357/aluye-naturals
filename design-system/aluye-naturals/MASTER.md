# Aluye Naturals — Master Design System

> Global source of truth for the Aluye Naturals e-commerce website.
> Before building a page, check `pages/[page-name].md`; page rules override this file.

**Project:** Aluye Naturals  
**Product:** Natural beauty and wellness e-commerce  
**Stack:** Semantic HTML, Tailwind CSS, Python/Flask  
**Brand line:** Body. Mind. Soul.  
**Direction:** West African botanical heritage meets modern editorial beauty retail  
**Reference:** Use Sephora UK for commerce density and discoverability, never for copied branding, layout, text, or assets.

## 1. Brand foundation

### Promise

Pure, effective care for skin, hair, beard, and body, rooted in natural ingredients and time-tested African beauty rituals.

### Proof points

- 100% unrefined shea butter sourced from trusted West African artisans.
- Raw, cold-pressed, plant-based ingredients.
- No unnecessary fillers, harsh chemicals, or synthetic additives.
- Ethical sourcing, small-batch care, and respect for the environment.
- Products designed to nourish the whole person: body, mind, and soul.

### Brand personality

Grounded, generous, sensorial, knowledgeable, warm, refined, and quietly confident.

### Voice

- Lead with the benefit, then explain the ingredient and ritual.
- Use plain, reassuring language rather than pseudo-scientific luxury jargon.
- Be specific about origin, texture, scent, use, and skin/hair concern.
- Say “crafted,” “nourishing,” “raw,” “unrefined,” “ritual,” and “radiance” sparingly.
- Do not make unverified medical, healing, SPF, acne-treatment, or hair-regrowth claims. Use compliant language such as “helps support,” “helps improve the appearance of,” and “formulated for.”

## 2. Visual direction

### Design concept: Modern Earth Editorial

The site should feel premium and product-rich without becoming cold. Use clean retail grids and strong black typography, softened by warm bone surfaces, kraft-paper tones, shea gold, clay, and restrained botanical green.

The current black containers and kraft labels are the visual anchor. Product photography stays crisp and mostly isolated on warm white backgrounds; editorial photography adds skin, ingredients, hands, landscape, and ritual.

### Do

- Use generous whitespace around products.
- Combine sharp retail structure with tactile natural details.
- Use thin borders, restrained shadows, and mostly square geometry.
- Let photography and ingredient color provide richness.
- Use serif display type for emotion and sans serif type for commerce.

### Avoid

- Liquid glass, glassmorphism, neon color, or iridescent effects.
- Copying Sephora’s black-and-white stripe motif or exact page compositions.
- Rustic craft-market styling, excessive leaf graphics, or faux-African patterns.
- Rounded “app-like” cards everywhere.
- Overpromising wellness or medical results.

## 3. Color system

| Token | Hex | Tailwind role | Usage |
|---|---:|---|---|
| `ink` | `#17130F` | primary-950 | Logo, headings, primary buttons |
| `charcoal` | `#2A2520` | primary-900 | Body emphasis, dark surfaces |
| `bark` | `#594A3B` | earth-700 | Secondary text, warm dark accents |
| `kraft` | `#B58A55` | gold-600 | Brand accent, ingredient highlights |
| `shea` | `#D4A85F` | gold-500 | Small highlights, badges, focus accents |
| `clay` | `#A8563A` | clay-600 | Editorial accent, limited promotional use |
| `botanical` | `#365C45` | green-800 | Sustainability and ingredient cues |
| `sage` | `#A7B39C` | green-300 | Soft section backgrounds |
| `bone` | `#F6F1E8` | stone-50 | Main warm background |
| `cream` | `#FCFAF6` | surface | Product and content surfaces |
| `sand` | `#E7D8C3` | stone-200 | Borders and muted blocks |
| `white` | `#FFFFFF` | white | Product image wells |
| `error` | `#A62C2C` | red-700 | Errors and destructive actions |
| `success` | `#2F6B45` | green-700 | Success feedback |

### Semantic rules

- Primary CTA: `ink` background with white text.
- CTA hover: `charcoal`; never shift layout.
- Secondary CTA: transparent with `ink` border.
- Promotional accent: use `clay` or `shea`, never both in the same component.
- Text on `bone`, `cream`, or white must use `ink`, `charcoal`, or `bark`.
- Reserve `botanical` for ingredient, sourcing, and sustainability contexts.
- Focus ring: 2px `shea` plus 2px offset.

## 4. Typography

### Families

- Display/headings: **Cormorant Garamond**, fallback Georgia, serif.
- UI/body: **Inter**, fallback Arial, sans-serif.

```css
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@500;600;700&family=Inter:wght@400;500;600;700&display=swap');
```

### Scale

| Role | Mobile | Desktop | Weight/leading |
|---|---|---|---|
| Display XL | 48px | 80px | 600 / 0.95 |
| H1 | 40px | 64px | 600 / 1.0 |
| H2 | 32px | 48px | 600 / 1.05 |
| H3 | 26px | 34px | 600 / 1.15 |
| Product title | 16px | 17px | 600 / 1.35, Inter |
| Body large | 18px | 20px | 400 / 1.65 |
| Body | 16px | 16px | 400 / 1.6 |
| Small | 14px | 14px | 400 / 1.5 |
| Label | 12px | 12px | 600 / 1.2, uppercase, 0.08em |

Keep editorial copy to 65–72 characters per line. Prices use tabular numerals.

## 5. Layout

- Mobile first at 375px.
- Breakpoints: `sm 640`, `md 768`, `lg 1024`, `xl 1280`, `2xl 1440`.
- Main container: max 1440px; gutters 16 / 24 / 32 / 48px.
- Reading container: max 760px.
- Spacing rhythm: 4, 8, 12, 16, 24, 32, 48, 64, 96, 128px.
- Product grid: 2 columns mobile, 3 tablet, 4 desktop; 16–24px gaps.
- Editorial sections: 64px mobile and 96–128px desktop vertical spacing.
- Image ratios: product `4:5`; category `1:1`; editorial hero `4:5` mobile and `16:7` desktop.

## 6. Commerce architecture

### Header

1. Utility/promotion bar: delivery threshold, seasonal offer, or ethical sourcing message.
2. Main header: menu, centered wordmark, search, account, wishlist, bag.
3. Desktop category navigation:
   - New & Best Sellers
   - Body
   - Face
   - Hair & Scalp
   - Beard & Grooming
   - Oils & Raw Essentials
   - Sets & Gifts
   - Our Story
4. Mega menus may group by product, concern, ingredient, and ritual.

Header is sticky after the hero threshold. On mobile, use a full-height drawer and keep search prominent.

### Discovery patterns

Borrow the useful retail logic seen on Sephora UK:

- New, trending, best-rated, and back-in-stock collections.
- Shop by category, concern, ingredient, routine, scent, and price.
- Editorial guides that lead naturally into products.
- Ratings, wishlist, badges, variant selectors, and quick add.
- Delivery threshold and promotional messaging visible early.

Aluye-specific discovery tools:

- “Find Your Ritual” quiz.
- “Shop by Ingredient” for shea, charcoal, black soap, rosehip, coconut, black seed, and tea tree.
- “Shop by Concern” for dryness, dullness, uneven-looking tone, cleansing, scalp care, and beard care.

## 7. Components

### Buttons

- Minimum height 48px; icon buttons minimum 44×44px.
- Primary buttons are square or 2–4px radius, not pills.
- Use one primary action per section.
- Loading state disables repeat submission and retains button width.

### Product card

- White or cream image well, `4:5`, product fully visible using `object-contain`.
- Optional badge at top left: New, Best Seller, Raw, Limited, or Low Stock.
- Wishlist icon top right with accessible label.
- Content: category/ritual label, product name, one-line benefit, rating/count, size/variant, price.
- Quick Add appears on desktop hover/focus and remains visible on touch devices.
- Card itself may link to product details; never nest conflicting interactive elements.
- Do not add heavy shadows. Use border/color change for hover.

### Badges

Small uppercase labels. Use `ink`, `botanical`, or `clay` backgrounds with accessible text. Avoid badge clutter; maximum two.

### Inputs and forms

- Always show persistent labels.
- Minimum height 48px and 16px input text.
- Validate on blur and place recovery-focused errors below fields.
- Preserve user-entered data after errors.
- Use semantic autocomplete values in checkout.

### Filters

- Desktop: left rail or horizontal toolbar with result count and sort.
- Mobile: bottom sheet/drawer with Apply and Clear actions.
- Show applied filters as removable chips.
- Updating results must announce count through `aria-live="polite"`.

### Cart

- Side drawer for quick review; dedicated cart page for editing.
- Show thumbnail, product/variant, quantity, price, remove, and delivery-progress message.
- Provide clear empty, loading, error, and success states.

## 8. Motion and interaction

- Duration: 150ms controls, 200–250ms drawers/cards, maximum 350ms page overlays.
- Animate opacity and transform only.
- No parallax or decorative continuous motion.
- Product image swap may crossfade.
- Respect `prefers-reduced-motion`; all functions remain usable without animation.
- Hover is enhancement only; every action must work by keyboard and touch.

## 9. Accessibility

- WCAG 2.2 AA target.
- Skip link and landmark-based page structure.
- Sequential heading hierarchy and one descriptive H1 per page.
- Visible `focus-visible` state on every interactive element.
- Product images require meaningful alt text; decorative textures use empty alt.
- Icon-only controls need accessible names.
- Color is never the only signal for sale, stock, selection, or errors.
- Modal/drawer focus is trapped and restored to its trigger.
- Touch targets are at least 44×44px.
- Price, quantity, validation, and cart updates are screen-reader announced.

## 10. Performance

- Convert photography to AVIF/WebP with JPEG fallback.
- Provide width, height, `srcset`, and `sizes` to prevent layout shift.
- Eager-load only the hero/LCP image; lazy-load below-fold assets.
- Use a similar fallback metric for web fonts and `font-display: swap`.
- Avoid Tailwind CDN in production; compile and purge CSS.
- Target LCP under 2.5s, CLS under 0.1, and INP under 200ms.

## 11. Tailwind and Python implementation

### Tailwind

- Map every semantic color and font into `tailwind.config.js`.
- Prefer reusable component classes or Jinja macros over repeated utility strings.
- Use `focus-visible:ring-2 focus-visible:ring-gold-500 focus-visible:ring-offset-2`.
- Use `motion-reduce:transition-none motion-reduce:transform-none`.

### Python/Flask

- Flask app factory with blueprints: `shop`, `cart`, `checkout`, `account`, `content`.
- Jinja base layout plus component macros for cards, prices, badges, forms, and pagination.
- Product/category data may begin as structured Python/JSON fixtures, then move behind a repository/service layer.
- Use server-rendered pages first; add small progressive-enhancement scripts only where useful.
- Validate all cart and checkout data server-side. Never trust prices from the browser.

## 12. Required page set

- Home
- Collection/search results
- Product detail
- Cart drawer and cart page
- Checkout
- Account/wishlist
- Our Story and ingredient journal
- Policy/help pages

## 13. Pre-delivery checklist

- No copied Sephora assets, text, stripe patterns, or proprietary styling.
- Product claims reviewed for cosmetic/regulatory compliance.
- Responsive at 375, 768, 1024, and 1440px.
- Keyboard-only purchase journey completed.
- Touch targets, labels, alt text, contrast, focus, and reduced motion verified.
- Empty/loading/error/out-of-stock states implemented.
- Product images optimized and dimensions reserved.
- Cart totals and checkout values recalculated server-side.
