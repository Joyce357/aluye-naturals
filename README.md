# Aluyè Naturals

> Small-batch care, rooted in nature.

A full-stack e-commerce website for Aluyè Naturals — a natural skincare,
haircare, beard care, and body care brand rooted in West African ingredients
and everyday ritual.

## Tech Stack

- Python / Flask backend
- Jinja2 templates
- SQLite database
- Vanilla JavaScript
- Tailwind CSS with custom design tokens

## Features

- Full product catalogue with category, tag, price, and rating filters
- Shopping cart, free-shipping progress, and guest checkout
- Product quick view, wishlist controls, ratings, and currency selection
- Responsive homepage merchandising and editorial content
- Contact form connected to the administrator inbox
- Blog / Journal
- Loyalty programme page
- SEO metadata, structured data, robots.txt, and sitemap.xml
- Lighthouse-verified accessibility and performance
- Protected administration dashboard with:
  - Product management and image uploads
  - Order management and tracking
  - Messages and notifications
  - Homepage and site settings
  - Payment-method configuration
  - Shipping zones and discount codes
  - Journal publishing
  - Analytics and CSV export
  - Administrator roles and activity logs

## Setup Instructions

1. Clone the repository:

   ```bash
   git clone https://github.com/Joyce357/aluye-naturals.git
   cd aluye-naturals
   ```

2. Create and activate a virtual environment:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

   macOS/Linux:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Install Python and frontend dependencies:

   ```bash
   pip install -r requirements.txt
   npm install
   npm run css:build
   ```

4. Copy `.env.example` to `.env` and replace every placeholder:

   ```powershell
   Copy-Item .env.example .env
   ```

5. Run the app:

   ```bash
   python app.py
   ```

6. Visit <http://127.0.0.1:5000>.

## Admin Panel

Visit <http://127.0.0.1:5000/admin>.

Set `ADMIN_USERNAME`, `ADMIN_PASSWORD`, and `ADMIN_EMAIL` in `.env` before
initializing a production database. Development fallbacks are provided only for
local setup and must not be used in production.

## Testing

```bash
python -m pytest -q
npm run css:build
```

Run the local Lighthouse audit:

```bash
npm run lighthouse
```

## Deployment

The application can be deployed to Railway, Render, or another platform that
supports Python/Flask. Configure all `.env.example` variables in the hosting
platform, set `SITE_URL` to the final HTTPS domain, and use a persistent volume
or managed database for production data.

## Security Notes

- Never commit `.env`, SQLite databases, payment secrets, or uploaded customer
  files.
- Payment secret fields are written server-side and are never rendered back to
  the browser.
- Replace the development Flask server with Waitress or another production WSGI
  server when deploying.

## License

© 2026 Aluyè Naturals. All rights reserved.
