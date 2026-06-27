# Aluyè Naturals — E-Commerce Website

Natural skin, hair, body and beard care rooted in West African ingredients.

Live site: https://aluye-naturals.onrender.com

## Tech Stack
- Python 3 / Flask
- SQLite (auto-created on startup)
- Jinja2 templates
- Vanilla JavaScript
- Tailwind CSS with custom design tokens
- Flask-Mail for emails
- Gunicorn for production

## Local Development Setup

1. Clone the repo:
```
git clone https://github.com/Joyce357/aluye-naturals
cd aluye-naturals
```

2. Create virtual environment:
```
python -m venv .venv
.venv\Scripts\activate    # Windows
source .venv/bin/activate  # Mac/Linux
```

3. Install dependencies:
```
pip install -r requirements.txt
```

4. Copy environment variables:
```
cp .env.example .env
```
Fill in your actual values in .env

5. Run the app:
```
python app.py
```

6. Visit: http://127.0.0.1:5000

## Admin Panel
- URL: http://127.0.0.1:5000/admin
- Username: admin
- Password: aluye2026

## Deployment
- Deployed on Render.com
- Domain managed on Hostinger

## Environment Variables
See `.env.example` for all required environment variables.
Set these in the Render dashboard under Environment.
