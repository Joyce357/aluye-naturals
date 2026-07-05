import csv
import io
import json
import os
import sqlite3
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path

from flask import (
    Blueprint,
    Response,
    abort,
    current_app,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename


admin_bp = Blueprint("admin", __name__, url_prefix="/admin")
PRODUCTS_REF = []
CATEGORIES_REF = []
BLOG_POSTS_REF = []

NAV_GROUPS = [
    ("core", "", [
        ("dashboard", "Dashboard"),
        ("global_settings", "Site Settings"),
    ]),
    ("commerce", "Commerce", [
        ("products", "Products"),
        ("orders", "Orders"),
        ("returns_admin", "Returns"),
        ("abandoned_admin", "Abandoned Carts"),
        ("discounts", "Discount Codes"),
        ("shipping", "Shipping & Delivery"),
    ]),
    ("marketing", "Marketing", [
        ("subscribers_admin", "Subscribers"),
        ("analytics", "Analytics"),
    ]),
    ("content", "Content", [
        ("homepage", "Homepage Editor"),
        ("journal", "Blog / Journal"),
        ("reviews_admin", "Reviews"),
        ("messages", "Messages / Inbox"),
        ("notifications", "Notifications"),
    ]),
    ("system", "System", [
        ("account", "Admin Users"),
        ("issues_admin", "Site Issues"),
    ]),
]

SITE_ISSUES = [
    {"priority": "Critical", "title": "Meta description showing broken \"trans-\" template variables", "status": "resolved"},
    {"priority": "Critical", "title": "Cart drawer X button not closing the cart", "status": "not_reproducible"},
    {"priority": "Critical", "title": "Site not responsive on mobile — product grid breaks on small screens", "status": "resolved"},
    {"priority": "Critical", "title": "Stock levels not reducing after an order is placed", "status": "resolved"},
    {"priority": "Critical", "title": "Discount popup not capturing emails correctly (no validation/feedback)", "status": "resolved"},
    {"priority": "High", "title": "WhatsApp button appearing on the live site", "status": "resolved"},
    {"priority": "High", "title": "Address showing full street address instead of Toronto, Ontario, Canada", "status": "resolved"},
    {"priority": "High", "title": "Welcome subscription email not sending to new subscribers", "status": "resolved"},
    {"priority": "High", "title": "Social media links not connected to real accounts", "status": "resolved"},
    {"priority": "High", "title": "Google showing stale/wrong SEO snippet (old WordPress placeholder text)", "status": "resolved"},
    {"priority": "Medium", "title": "Product images showing in circular format — should be square", "status": "not_reproducible"},
    {"priority": "Medium", "title": "Maintenance mode not readily usable during development", "status": "resolved"},
    {"priority": "Medium", "title": "No coming soon page for new visitors", "status": "skipped"},
    {"priority": "Medium", "title": "Footer accordion not working on mobile", "status": "not_reproducible"},
    {"priority": "Medium", "title": "Service worker intercepting admin routes and showing offline page", "status": "resolved"},
    {"priority": "Medium", "title": "Admin settings tab resets to General after saving (looked like save was broken)", "status": "resolved"},
    {"priority": "Medium", "title": "Admin-configured SMTP settings were saved but never actually used for sending mail", "status": "resolved"},
    {"priority": "Medium", "title": "Flask-Mail package missing from the environment, causing email sends to silently fail/crash", "status": "resolved"},
    {"priority": "Medium", "title": "Admin SEO tab (meta title/description, Search Console, GA, FB Pixel) was entirely non-functional", "status": "resolved"},
    {"priority": "Medium", "title": "PayPal checkout integration — built to spec, not yet tested against a real PayPal account", "status": "open"},
    {"priority": "Low", "title": "Currency selector in footer showing incorrect defaults", "status": "resolved"},
    {"priority": "Low", "title": "Some admin sidebar links leading to placeholder pages", "status": "not_reproducible"},
    {"priority": "Low", "title": "Missing OG image for social sharing", "status": "not_reproducible"},
    {"priority": "Low", "title": "Product photos are a mix of JPG/PNG and WebP — could standardize on WebP for smaller file size", "status": "open"},
    {"priority": "Low", "title": "Legacy \"Payment Methods\" admin page duplicated the real PayPal/Stripe/Flutterwave/Paystack settings in Integrations — removed", "status": "resolved"},
    {"priority": "Low", "title": "Tax rate setting exists in admin but isn't applied to checkout totals", "status": "open"},
]

NAV_ITEMS = [(key, label) for _, _, items in NAV_GROUPS for key, label in items]


def init_admin(app, products, categories, blog_posts):
    global PRODUCTS_REF, CATEGORIES_REF, BLOG_POSTS_REF
    PRODUCTS_REF = products
    CATEGORIES_REF = categories
    BLOG_POSTS_REF = blog_posts
    app.config.setdefault(
        "ADMIN_DATABASE", str(Path(app.instance_path) / "aluye_admin.db")
    )
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    app.register_blueprint(admin_bp)
    with app.app_context():
        init_db()
        sync_products_to_db()
        reload_products_from_db()
        reload_blog_posts_from_db()
    if not app.config.get("TESTING"):
        start_abandoned_cart_scheduler(app)


def get_db():
    if "admin_db" not in g:
        g.admin_db = sqlite3.connect(current_app.config["ADMIN_DATABASE"])
        g.admin_db.row_factory = sqlite3.Row
    return g.admin_db


def close_db(_error=None):
    db = g.pop("admin_db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS admin_users (
          id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL, name TEXT NOT NULL,
          email TEXT, password_hash TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'Super Admin'
        );
        CREATE TABLE IF NOT EXISTS products (
          slug TEXT PRIMARY KEY, data TEXT NOT NULL, stock INTEGER NOT NULL DEFAULT 20,
          status TEXT NOT NULL DEFAULT 'active', updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS orders (
          id INTEGER PRIMARY KEY AUTOINCREMENT, order_number TEXT UNIQUE NOT NULL,
          customer_name TEXT NOT NULL, email TEXT, address TEXT, items TEXT NOT NULL,
          total REAL NOT NULL, status TEXT NOT NULL DEFAULT 'Pending',
          tracking TEXT DEFAULT '', payment_method TEXT DEFAULT 'Online payment',
          created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS messages (
          id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, email TEXT NOT NULL,
          subject TEXT NOT NULL, message TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'unread',
          created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS notifications (
          id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL, title TEXT NOT NULL,
          detail TEXT NOT NULL, is_read INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS settings (
          key TEXT PRIMARY KEY, value TEXT NOT NULL, updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS discounts (
          id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE NOT NULL, type TEXT NOT NULL,
          value REAL NOT NULL, minimum REAL DEFAULT 0, expiry TEXT, usage_limit INTEGER DEFAULT 0,
          used INTEGER DEFAULT 0, enabled INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS shipping_zones (
          id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, rate REAL NOT NULL,
          threshold REAL NOT NULL, delivery_days TEXT NOT NULL, enabled INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS blog_posts (
          id INTEGER PRIMARY KEY AUTOINCREMENT, slug TEXT UNIQUE NOT NULL, title TEXT NOT NULL,
          category TEXT NOT NULL, body TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS analytics (
          path TEXT PRIMARY KEY, views INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS product_events (
          slug TEXT PRIMARY KEY, views INTEGER NOT NULL DEFAULT 0, cart_adds INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS activity (
          id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL, action TEXT NOT NULL,
          created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS subscribers (
          id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE NOT NULL, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS reviews (
          id INTEGER PRIMARY KEY AUTOINCREMENT, product_slug TEXT NOT NULL, name TEXT NOT NULL,
          email TEXT NOT NULL, rating INTEGER NOT NULL, title TEXT NOT NULL, body TEXT NOT NULL,
          photo TEXT DEFAULT '', status TEXT NOT NULL DEFAULT 'pending',
          created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS wishlist (
          id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, product_slug TEXT NOT NULL,
          created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS ugc_photos (
          id INTEGER PRIMARY KEY AUTOINCREMENT, image TEXT NOT NULL, customer_name TEXT NOT NULL,
          product_slug TEXT DEFAULT '', active INTEGER DEFAULT 1, sort_order INTEGER DEFAULT 0,
          created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS abandoned_carts (
          id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT NOT NULL, items TEXT NOT NULL,
          total REAL NOT NULL, reminded INTEGER DEFAULT 0, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS return_requests (
          id INTEGER PRIMARY KEY AUTOINCREMENT, reference TEXT UNIQUE NOT NULL,
          order_number TEXT NOT NULL, email TEXT NOT NULL, items TEXT NOT NULL,
          reason TEXT NOT NULL, details TEXT DEFAULT '', refund_method TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'Pending', admin_note TEXT DEFAULT '',
          created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS waitlist (
          id INTEGER PRIMARY KEY AUTOINCREMENT, product_slug TEXT NOT NULL, email TEXT NOT NULL,
          created_at TEXT NOT NULL, UNIQUE(product_slug, email)
        );
        CREATE TABLE IF NOT EXISTS referrals (
          id INTEGER PRIMARY KEY AUTOINCREMENT, referrer_code TEXT NOT NULL,
          referred_email TEXT, status TEXT NOT NULL DEFAULT 'pending',
          created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS loyalty_points (
          id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, action TEXT NOT NULL,
          points INTEGER NOT NULL, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS quiz_responses (
          id INTEGER PRIMARY KEY AUTOINCREMENT, skin_type TEXT, skin_concern TEXT,
          hair_concern TEXT, beard TEXT, budget TEXT, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS message_replies (
          id INTEGER PRIMARY KEY AUTOINCREMENT, message_id INTEGER NOT NULL,
          reply_text TEXT NOT NULL, replied_by TEXT NOT NULL,
          created_at TEXT NOT NULL,
          FOREIGN KEY(message_id) REFERENCES messages(id)
        );
        CREATE TABLE IF NOT EXISTS message_drafts (
          message_id INTEGER PRIMARY KEY, draft_text TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          FOREIGN KEY(message_id) REFERENCES messages(id)
        );
        CREATE TABLE IF NOT EXISTS customers (
          id INTEGER PRIMARY KEY AUTOINCREMENT, first_name TEXT NOT NULL,
          last_name TEXT NOT NULL, email TEXT UNIQUE NOT NULL,
          password_hash TEXT NOT NULL, phone TEXT DEFAULT '',
          address TEXT DEFAULT '', city TEXT DEFAULT '',
          state TEXT DEFAULT '', postal_code TEXT DEFAULT '',
          country TEXT DEFAULT '', created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS stock_log (
          id INTEGER PRIMARY KEY AUTOINCREMENT, product_slug TEXT NOT NULL,
          change_qty INTEGER NOT NULL, reason TEXT NOT NULL, reference TEXT DEFAULT '',
          stock_after INTEGER NOT NULL, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS gift_cards (
          id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE NOT NULL,
          original_value REAL NOT NULL, remaining REAL NOT NULL,
          from_name TEXT DEFAULT '', to_name TEXT DEFAULT '',
          to_email TEXT DEFAULT '', message TEXT DEFAULT '',
          status TEXT NOT NULL DEFAULT 'active',
          created_at TEXT NOT NULL, expires_at TEXT NOT NULL
        );
        """
    )
    try:
        db.execute("ALTER TABLE subscribers ADD COLUMN source TEXT DEFAULT 'website'")
    except sqlite3.OperationalError:
        pass
    try:
        db.execute("ALTER TABLE shipping_zones ADD COLUMN postal_prefixes TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass
    try:
        db.execute("ALTER TABLE orders ADD COLUMN transaction_id TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass
    try:
        db.execute("ALTER TABLE orders ADD COLUMN shipping_fee REAL DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    try:
        db.execute("ALTER TABLE orders ADD COLUMN phone TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass
    try:
        db.execute("ALTER TABLE notifications ADD COLUMN related_type TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass
    try:
        db.execute("ALTER TABLE notifications ADD COLUMN related_id TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass
    try:
        db.execute("ALTER TABLE notifications ADD COLUMN archived INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    if not db.execute("SELECT 1 FROM admin_users LIMIT 1").fetchone():
        db.execute(
            "INSERT INTO admin_users(username,name,email,password_hash,role) VALUES(?,?,?,?,?)",
            (
                os.environ.get("ADMIN_USERNAME", "admin"),
                "Aluyè Administrator",
                os.environ.get("ADMIN_EMAIL", "admin@aluyenaturals.com"),
                generate_password_hash(
                    os.environ.get("ADMIN_PASSWORD", "aluye2026")
                ),
                "Super Admin",
            ),
        )
    if not db.execute("SELECT 1 FROM shipping_zones LIMIT 1").fetchone():
        db.executemany(
            "INSERT INTO shipping_zones(name,rate,threshold,delivery_days,postal_prefixes) VALUES(?,?,?,?,?)",
            [
                ("Ontario (local)", 8, 0, "1–3 business days", "K,L,M,N,P"),
                ("Rest of Canada", 15, 0, "3–7 business days", ""),
                ("United States", 25, 0, "5–10 business days", ""),
                ("Rest of World", 35, 0, "10–21 business days", ""),
            ],
        )
    if not db.execute("SELECT 1 FROM discounts LIMIT 1").fetchone():
        db.executemany(
            "INSERT INTO discounts(code,type,value,minimum,expiry,usage_limit,used) VALUES(?,?,?,?,?,?,?)",
            [
                ("RITUAL15", "percent", 15, 50, "2026-12-31", 500, 37),
                ("WELCOME10", "fixed", 10, 40, "2026-09-30", 250, 82),
                ("RITUAL10", "percent", 10, 0, "2027-12-31", 0, 0),
            ],
        )
    if not db.execute("SELECT 1 FROM orders LIMIT 1").fetchone():
        now = datetime.now()
        for index in range(5):
            created = (now - timedelta(days=index)).isoformat(timespec="minutes")
            db.execute(
                """INSERT INTO orders(order_number,customer_name,email,address,items,total,status,created_at,updated_at)
                   VALUES(?,?,?,?,?,?,?,?,?)""",
                (
                    f"AN-2026{105-index}",
                    ["Joyce A.", "Amara K.", "Nia B.", "Malik T.", "Aisha O."][index],
                    f"customer{index+1}@example.com",
                    "Customer shipping address",
                    json.dumps([{"name": PRODUCTS_REF[index]["name"], "quantity": 1}]),
                    float(PRODUCTS_REF[index]["price"]),
                    ["Pending", "Processing", "Shipped", "Delivered", "Delivered"][index],
                    created,
                    created,
                ),
            )
    db.commit()


def sync_products_to_db():
    db = get_db()
    if db.execute("SELECT COUNT(*) c FROM products").fetchone()["c"]:
        return
    now = datetime.now().isoformat(timespec="minutes")
    for product in PRODUCTS_REF:
        db.execute(
            """INSERT INTO products(slug,data,stock,status,updated_at) VALUES(?,?,?,?,?)
               ON CONFLICT(slug) DO NOTHING""",
            (product["slug"], json.dumps(product), 20, "active", now),
        )
    db.commit()


def reload_products_from_db():
    rows = get_db().execute(
        "SELECT data FROM products WHERE status='active' ORDER BY rowid"
    ).fetchall()
    PRODUCTS_REF[:] = [json.loads(row["data"]) for row in rows]


def reload_blog_posts_from_db():
    rows = get_db().execute(
        "SELECT slug,title,category,body FROM blog_posts WHERE status='published' ORDER BY created_at"
    ).fetchall()
    managed_slugs = {
        row["slug"]
        for row in get_db().execute("SELECT slug FROM blog_posts").fetchall()
    }
    BLOG_POSTS_REF[:] = [
        post for post in BLOG_POSTS_REF if post["slug"] not in managed_slugs
    ]
    for row in rows:
        paragraphs = [
            paragraph.strip()
            for paragraph in row["body"].splitlines()
            if paragraph.strip()
        ]
        BLOG_POSTS_REF.append(
            {
                "slug": row["slug"],
                "tag": row["category"],
                "title": row["title"],
                "excerpt": row["body"][:160],
                "body": paragraphs or [row["body"]],
            }
        )


def load_setting(key, default=None):
    row = get_db().execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    if not row:
        return default
    try:
        return json.loads(row["value"])
    except json.JSONDecodeError:
        return row["value"]


def save_setting(key, value):
    get_db().execute(
        """INSERT INTO settings(key,value,updated_at) VALUES(?,?,?)
           ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at""",
        (key, json.dumps(value), datetime.now().isoformat(timespec="minutes")),
    )
    get_db().commit()


def save_env_secret(name, value):
    env_path = Path(current_app.root_path) / ".env"
    lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
    prefix = f"{name}="
    replacement = f"{name}={value}"
    updated = False
    for index, line in enumerate(lines):
        if line.startswith(prefix):
            lines[index] = replacement
            updated = True
            break
    if not updated:
        lines.append(replacement)
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def record_activity(action):
    get_db().execute(
        "INSERT INTO activity(username,action,created_at) VALUES(?,?,?)",
        (
            session.get("admin_username", "system"),
            action,
            datetime.now().isoformat(timespec="minutes"),
        ),
    )
    get_db().commit()


def add_notification(kind, title, detail, related_type="", related_id=""):
    get_db().execute(
        """INSERT INTO notifications(kind,title,detail,created_at,related_type,related_id)
           VALUES(?,?,?,?,?,?)""",
        (kind, title, detail, datetime.now().isoformat(timespec="minutes"), related_type, related_id),
    )
    get_db().commit()


def record_page_view(path):
    db = get_db()
    db.execute(
        """INSERT INTO analytics(path,views) VALUES(?,1)
           ON CONFLICT(path) DO UPDATE SET views=views+1""",
        (path,),
    )
    db.commit()


def record_product_event(slug, event):
    column = "views" if event == "view" else "cart_adds"
    db = get_db()
    db.execute(
        "INSERT INTO product_events(slug,views,cart_adds) VALUES(?,0,0) ON CONFLICT(slug) DO NOTHING",
        (slug,),
    )
    db.execute(f"UPDATE product_events SET {column}={column}+1 WHERE slug=?", (slug,))
    db.commit()


def save_contact_message(name, email, subject, message):
    db = get_db()
    cursor = db.execute(
        "INSERT INTO messages(name,email,subject,message,created_at) VALUES(?,?,?,?,?)",
        (name, email, subject, message, datetime.now().isoformat(timespec="minutes")),
    )
    db.commit()
    add_notification(
        "message", "New contact message", f"{name}: {subject}",
        related_type="message", related_id=str(cursor.lastrowid),
    )


def send_inquiry_autoresponse(name, email):
    from flask import current_app, render_template

    settings = load_setting("settings", {}) or {}
    if settings.get("inquiry_autoresponse_enabled", True) is False:
        return False

    html_body = render_template(
        "emails/inquiry_autoresponse.html",
        customer_name=name,
        autoresponse_message=settings.get(
            "inquiry_autoresponse_message",
            "Thank you for reaching out to Aluyè Naturals. We've received your message and will reply within two business days.",
        ),
    )
    success, error = send_mail(
        subject=settings.get("inquiry_autoresponse_subject") or "We've received your message 🌿",
        recipients=[email],
        html=html_body,
    )
    if not success:
        add_notification("email_error", "Inquiry auto-response failed", f"{email}: {error}")
    return success


def check_abandoned_carts(app):
    with app.test_request_context("/"):
        settings = load_setting("settings", {}) or {}
        if not settings.get("abandoned_cart_enabled"):
            return
        try:
            delay_hours = float(settings.get("abandoned_cart_delay_hours") or 24)
        except (TypeError, ValueError):
            delay_hours = 24
        cutoff = (datetime.now() - timedelta(hours=delay_hours)).isoformat(timespec="minutes")

        db = get_db()
        rows = db.execute(
            "SELECT * FROM abandoned_carts WHERE reminded=0 AND created_at<=?", (cutoff,)
        ).fetchall()
        for row in rows:
            items = json.loads(row["items"])
            html_body = render_template(
                "emails/abandoned_cart.html",
                items=items,
                total=row["total"],
                reminder_message=settings.get(
                    "abandoned_cart_message",
                    "Your ritual is still waiting for you. Complete your order before it sells out.",
                ),
                site_url=app.config.get("SITE_URL", ""),
            )
            success, error = send_mail(
                subject=settings.get("abandoned_cart_subject") or "You left something in your cart 🌿",
                recipients=[row["email"]],
                html=html_body,
            )
            if not success:
                add_notification("email_error", "Abandoned cart email failed", f"{row['email']}: {error}")
            db.execute("UPDATE abandoned_carts SET reminded=1 WHERE id=?", (row["id"],))
        db.commit()


def start_abandoned_cart_scheduler(app):
    from apscheduler.schedulers.background import BackgroundScheduler

    scheduler = BackgroundScheduler(daemon=True)
    scheduler.add_job(lambda: check_abandoned_carts(app), "interval", minutes=30)
    scheduler.start()
    return scheduler


def get_admin_email():
    settings = load_setting("settings", {}) or {}
    return (
        settings.get("admin_email")
        or settings.get("contact_email")
        or os.environ.get("ADMIN_EMAIL", "admin@aluyenaturals.com")
    )


def send_mail(subject, recipients, html, reply_to=None):
    """Send an email using admin-configured SMTP settings (Global Settings -> Integrations),
    falling back to environment variables. Returns (success, error_message)."""
    from flask import current_app

    try:
        from flask_mail import Mail, Message as MailMessage
    except ImportError as exc:
        print(f"Email send failed ({subject} -> {recipients}): flask_mail not installed ({exc})")
        return False, "Email is not available (flask_mail is not installed on the server)."

    settings = load_setting("settings", {}) or {}
    mail_server = settings.get("mail_server") or current_app.config.get("MAIL_SERVER")
    mail_port = settings.get("mail_port") or current_app.config.get("MAIL_PORT")
    mail_username = settings.get("mail_username") or current_app.config.get("MAIL_USERNAME")
    mail_password = os.environ.get("MAIL_PASSWORD") or current_app.config.get("MAIL_PASSWORD")
    sender_email = settings.get("contact_email") or mail_username or current_app.config.get(
        "MAIL_DEFAULT_SENDER"
    )

    current_app.config["MAIL_SERVER"] = mail_server
    try:
        current_app.config["MAIL_PORT"] = int(mail_port)
    except (TypeError, ValueError):
        pass
    current_app.config["MAIL_USERNAME"] = mail_username
    current_app.config["MAIL_PASSWORD"] = mail_password
    current_app.config["MAIL_DEFAULT_SENDER"] = sender_email
    current_app.config["MAIL_SUPPRESS_SEND"] = not mail_username

    try:
        mail = Mail(current_app)
        msg = MailMessage(
            subject=subject,
            sender=("Aluyè Naturals", sender_email) if sender_email else None,
            recipients=recipients,
            html=html,
            reply_to=reply_to,
        )
        mail.send(msg)
        return True, None
    except Exception as exc:
        print(f"Email send failed ({subject} -> {recipients}): {exc}")
        return False, str(exc)


def send_welcome_email(email, source="website"):
    from flask import current_app, render_template

    settings = load_setting("settings", {}) or {}
    if settings.get("welcome_email_enabled", True) is False:
        return False

    first_name = email.split("@")[0].replace(".", " ").replace("_", " ").title()
    discount_code = settings.get("welcome_discount_code") or ("RITUAL10" if source == "exit_popup" else "RITUAL15")
    discount_percent = 10 if source == "exit_popup" else 15
    featured_products = [p for p in PRODUCTS_REF if "Best Seller" in p.get("tags", [])][:3]

    html_body = render_template(
        "emails/welcome.html",
        first_name=first_name,
        email=email,
        discount_code=discount_code,
        discount_percent=discount_percent,
        custom_message=settings.get("welcome_email_body", ""),
        featured_products=featured_products,
        site_url=current_app.config.get("SITE_URL", ""),
    )
    subject = settings.get("welcome_email_subject") or (
        "Welcome to Aluyè Naturals 🌿 — Your exclusive "
        f"{discount_percent}% off is inside"
    )
    success, error = send_mail(
        subject=subject,
        recipients=[email],
        html=html_body,
    )
    if not success:
        add_notification("email_error", "Welcome email failed", f"{email}: {error}")
    return success


def send_order_status_email(order, new_status, tracking=""):
    from flask import current_app, render_template

    settings = load_setting("settings", {}) or {}
    key = new_status.lower()
    if settings.get(f"{key}_email_enabled", True) is False:
        return False
    if not order["email"]:
        return False

    default_subject = f"Your Aluyè Naturals order {order['order_number']} has {'shipped' if key == 'shipped' else 'been delivered'} 🌿"
    default_message = (
        "Your order is on its way to you."
        if key == "shipped"
        else "Your order has been delivered. We hope you love your ritual."
    )
    html_body = render_template(
        "emails/order_status.html",
        customer_name=order["customer_name"],
        order_number=order["order_number"],
        status_heading=f"Your order has {'shipped' if key == 'shipped' else 'been delivered'}",
        status_message=settings.get(f"{key}_email_message") or default_message,
        tracking=tracking,
        contact_email=settings.get("contact_email", ""),
        site_url=current_app.config.get("SITE_URL", ""),
    )
    success, error = send_mail(
        subject=settings.get(f"{key}_email_subject") or default_subject,
        recipients=[order["email"]],
        html=html_body,
    )
    if not success:
        add_notification("email_error", f"{new_status} email failed", f"{order['order_number']}: {error}")
    return success


CANADIAN_PROVINCE_PREFIXES = {
    "AB": "T", "BC": "V", "MB": "R", "NB": "E", "NL": "A", "NS": "B",
    "ON": "KLMNP", "PE": "C", "QC": "GHJ", "SK": "S", "NT": "X", "NU": "X", "YT": "Y",
}


def calculate_shipping(postal_code, country, method="standard"):
    """Zone-based shipping calculation (no external geocoding API).
    Returns dict: {available, rate, zone_name, needs_quote}."""
    settings = load_setting("settings", {}) or {}
    if method == "pickup" and settings.get("shipping_pickup_enabled"):
        return {"available": True, "rate": 0.0, "zone_name": "Local pickup", "needs_quote": False}

    country_norm = (country or "").strip().lower()
    postal_norm = (postal_code or "").strip().upper().replace(" ", "")
    fsa_letter = postal_norm[0] if postal_norm else ""
    is_canada = "canada" in country_norm or country_norm in ("ca", "can")
    is_usa = country_norm in ("us", "usa", "united states", "united states of america")

    zones = get_db().execute("SELECT * FROM shipping_zones WHERE enabled=1").fetchall()

    if is_canada:
        for zone in zones:
            prefixes = [p.strip() for p in (zone["postal_prefixes"] or "").split(",") if p.strip()]
            if prefixes and fsa_letter in prefixes:
                return {"available": True, "rate": zone["rate"], "zone_name": zone["name"], "needs_quote": False}
        for zone in zones:
            if not (zone["postal_prefixes"] or "").strip() and "canada" in zone["name"].lower():
                return {"available": True, "rate": zone["rate"], "zone_name": zone["name"], "needs_quote": False}
    elif is_usa:
        for zone in zones:
            if "united states" in zone["name"].lower():
                return {"available": True, "rate": zone["rate"], "zone_name": zone["name"], "needs_quote": False}
    else:
        for zone in zones:
            if "rest of world" in zone["name"].lower():
                return {"available": True, "rate": zone["rate"], "zone_name": zone["name"], "needs_quote": False}

    needs_quote = bool(settings.get("shipping_manual_quote_enabled"))
    return {"available": False, "rate": None, "zone_name": None, "needs_quote": needs_quote}


def calculate_distance_shipping(address, city, postal_code, country, method="standard", subtotal=0):
    """Distance-based shipping via the Google Maps Distance Matrix API, using an
    admin-configured base fee + per-km rate from the store's origin address.
    Returns None (caller should fall back to calculate_shipping) when the feature
    is disabled, the API key isn't configured, or the address can't be resolved.
    Returns dict: {available, rate, zone_name, needs_quote, distance_km}."""
    import google_maps_client

    settings = load_setting("settings", {}) or {}
    if not settings.get("distance_shipping_enabled"):
        return None
    if not google_maps_client.is_configured(settings):
        return None
    if method == "pickup" and settings.get("shipping_pickup_enabled"):
        return {"available": True, "rate": 0.0, "zone_name": "Local pickup", "needs_quote": False, "distance_km": 0}

    destination = ", ".join(part for part in [address, city, postal_code, country] if part)
    if not destination:
        return None

    origin = settings.get("shipping_origin_address") or "Toronto, Ontario, Canada"
    distance_km = google_maps_client.get_distance_km(origin, destination, settings)
    if distance_km is None:
        return None

    try:
        max_distance = float(settings.get("shipping_max_distance_km") or 0)
    except (TypeError, ValueError):
        max_distance = 0
    if max_distance and distance_km > max_distance:
        return {
            "available": False, "rate": None, "zone_name": None,
            "needs_quote": bool(settings.get("shipping_manual_quote_enabled")),
            "distance_km": distance_km,
        }

    if settings.get("shipping_free_delivery_enabled"):
        try:
            free_minimum = float(settings.get("shipping_free_delivery_minimum") or 0)
        except (TypeError, ValueError):
            free_minimum = 0
        if subtotal >= free_minimum:
            return {"available": True, "rate": 0.0, "zone_name": "Free delivery", "needs_quote": False, "distance_km": distance_km}

    try:
        base_fee = float(settings.get("shipping_base_fee") or 0)
    except (TypeError, ValueError):
        base_fee = 0
    try:
        per_km_rate = float(settings.get("shipping_per_km_rate") or 0)
    except (TypeError, ValueError):
        per_km_rate = 0

    rate = round(base_fee + distance_km * per_km_rate, 2)
    return {
        "available": True, "rate": rate,
        "zone_name": f"Distance-based delivery ({distance_km:.1f} km)",
        "needs_quote": False, "distance_km": distance_km,
    }


def save_order(
    order_number,
    customer,
    items,
    subtotal,
    shipping_fee=0,
    payment_method="PayPal",
    status="Pending",
    transaction_id="",
):
    db = get_db()
    total = subtotal + shipping_fee
    db.execute(
        """INSERT OR IGNORE INTO orders(order_number,customer_name,email,address,items,total,status,
           payment_method,transaction_id,shipping_fee,phone,created_at,updated_at)
           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            order_number,
            f"{customer['first_name']} {customer['last_name']}",
            customer["email"],
            ", ".join(
                [
                    customer["address"],
                    customer["city"],
                    customer["postal_code"],
                    customer["country"],
                ]
            ),
            json.dumps(
                [
                    {
                        "slug": item["product"]["slug"],
                        "name": item["product"]["name"],
                        "quantity": item["quantity"],
                        "total": item["line_total"],
                    }
                    for item in items
                ]
            ),
            total,
            status,
            payment_method,
            transaction_id,
            shipping_fee,
            customer.get("phone", ""),
            datetime.now().isoformat(timespec="minutes"),
            datetime.now().isoformat(timespec="minutes"),
        ),
    )
    db.commit()
    order_row = db.execute("SELECT id FROM orders WHERE order_number=?", (order_number,)).fetchone()
    add_notification(
        "order", "New order placed", f"{order_number} · CAD ${total:.2f}",
        related_type="order", related_id=str(order_row["id"]) if order_row else "",
    )
    return total


def log_stock_change(product_slug, change_qty, reason, stock_after, reference=""):
    get_db().execute(
        """INSERT INTO stock_log(product_slug,change_qty,reason,reference,stock_after,created_at)
           VALUES(?,?,?,?,?,?)""",
        (product_slug, change_qty, reason, reference, stock_after, datetime.now().isoformat(timespec="minutes")),
    )


def deduct_stock(items, reference=""):
    db = get_db()
    for item in items:
        slug = item["product"]["slug"]
        quantity = item["quantity"]
        row = db.execute("SELECT stock FROM products WHERE slug=?", (slug,)).fetchone()
        if not row:
            continue
        new_stock = max(0, row["stock"] - quantity)
        db.execute("UPDATE products SET stock=? WHERE slug=?", (new_stock, slug))
        log_stock_change(slug, -quantity, "order_placed", new_stock, reference=reference)
        if new_stock < 5:
            add_notification(
                "stock", "Low stock alert", f"{item['product']['name']} has {new_stock} units remaining."
            )
    db.commit()


def restore_stock(order_items, reference=""):
    db = get_db()
    for item in order_items:
        slug = item.get("slug")
        if not slug:
            continue
        db.execute(
            "UPDATE products SET stock = stock + ? WHERE slug=?",
            (item["quantity"], slug),
        )
        row = db.execute("SELECT stock FROM products WHERE slug=?", (slug,)).fetchone()
        if row:
            log_stock_change(slug, item["quantity"], "order_cancelled", row["stock"], reference=reference)
    db.commit()


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("admin_user_id"):
            return redirect(url_for("admin.login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


@admin_bp.before_request
def protect_admin():
    if request.endpoint in {"admin.login", "admin.static"}:
        return None
    if not session.get("admin_user_id"):
        return redirect(url_for("admin.login", next=request.path))
    if session.get("admin_role") == "Editor" and request.endpoint in {
        "admin.shipping",
        "admin.discounts",
        "admin.account",
    }:
        flash("Your Editor role does not have permission to access that section.", "error")
        return redirect(url_for("admin.dashboard"))
    return None


@admin_bp.app_context_processor
def inject_admin_context():
    if not request.path.startswith("/admin"):
        return {}
    db = get_db()
    return {
        "admin_nav": NAV_ITEMS,
        "admin_nav_groups": NAV_GROUPS,
        "admin_user": {
            "name": session.get("admin_name", "Administrator"),
            "role": session.get("admin_role", "Super Admin"),
        },
        "admin_unread_messages": db.execute(
            "SELECT COUNT(*) c FROM messages WHERE status='unread'"
        ).fetchone()["c"],
        "admin_unread_notifications": db.execute(
            "SELECT COUNT(*) c FROM notifications WHERE is_read=0 AND archived=0"
        ).fetchone()["c"],
    }


@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = get_db().execute(
            "SELECT * FROM admin_users WHERE username=?", (username,)
        ).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session.update(
                admin_user_id=user["id"],
                admin_username=user["username"],
                admin_name=user["name"],
                admin_role=user["role"],
            )
            record_activity("Signed in")
            return redirect(request.args.get("next") or url_for("admin.dashboard"))
        flash("Incorrect username or password.", "error")
    return render_template("admin/login.html")


@admin_bp.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("admin.login"))


@admin_bp.get("/")
def dashboard():
    db = get_db()
    period = request.args.get("period", "month")
    period_days = {"today": 1, "week": 7, "month": 30}.get(period, 30)
    cutoff = (datetime.now() - timedelta(days=period_days)).isoformat(timespec="minutes")
    all_orders = db.execute("SELECT * FROM orders ORDER BY created_at DESC").fetchall()
    orders = [order for order in all_orders if order["created_at"] >= cutoff]
    revenue = sum(row["total"] for row in orders if row["status"] != "Cancelled")
    low_stock = db.execute(
        "SELECT COUNT(*) c FROM products WHERE stock < 5"
    ).fetchone()["c"]
    metrics = [
        ("Total revenue", f"${revenue:,.2f}", "This month"),
        ("Total orders", len(orders), f"{sum(o['status']=='Pending' for o in all_orders)} pending"),
        ("Total products", len(PRODUCTS_REF), "Live catalogue"),
        (
            "New messages",
            db.execute("SELECT COUNT(*) c FROM messages WHERE status='unread'").fetchone()["c"],
            "Unread inbox",
        ),
        ("Low stock alerts", low_stock, "Below 5 units"),
    ]
    chart = [42, 48, 46, 60, 58, 72, 68, 80, 77, 92, 88, 105]
    return render_template(
        "admin/dashboard.html",
        admin_section="dashboard",
        metrics=metrics,
        recent_orders=orders[:5],
        chart=chart,
        period=period,
    )


@admin_bp.route("/products", methods=["GET", "POST"])
def products():
    db = get_db()
    if request.method == "POST":
        action = request.form.get("bulk_action")
        selected = request.form.getlist("selected")
        if selected:
            if action == "delete":
                db.executemany("DELETE FROM products WHERE slug=?", [(s,) for s in selected])
                PRODUCTS_REF[:] = [p for p in PRODUCTS_REF if p["slug"] not in selected]
            elif action in {"active", "draft"}:
                db.executemany(
                    "UPDATE products SET status=? WHERE slug=?",
                    [(action, s) for s in selected],
                )
            db.commit()
            reload_products_from_db()
            for selected_slug in selected:
                row = db.execute(
                    "SELECT stock,data FROM products WHERE slug=?", (selected_slug,)
                ).fetchone()
                if row and row["stock"] < 5:
                    add_notification(
                        "stock",
                        "Low stock alert",
                        f"{json.loads(row['data'])['name']} has {row['stock']} units remaining.",
                    )
            record_activity(f"Bulk product action: {action}")
            flash("Products updated.", "success")
        return redirect(url_for("admin.products"))
    rows = db.execute("SELECT * FROM products ORDER BY updated_at DESC").fetchall()
    product_rows = [
        {**dict(row), "product": json.loads(row["data"])} for row in rows
    ]
    return render_template(
        "admin/products.html",
        admin_section="products",
        products=product_rows,
        categories=CATEGORIES_REF,
    )


@admin_bp.route("/products/stock-log")
def stock_log():
    db = get_db()
    rows = db.execute(
        "SELECT * FROM stock_log ORDER BY id DESC LIMIT 200"
    ).fetchall()
    return render_template(
        "admin/stock_log.html",
        admin_section="products",
        entries=rows,
    )


@admin_bp.route("/products/new", methods=["GET", "POST"])
@admin_bp.route("/products/<slug>/edit", methods=["GET", "POST"])
def product_form(slug=None):
    db = get_db()
    existing = None
    if slug:
        row = db.execute("SELECT * FROM products WHERE slug=?", (slug,)).fetchone()
        if row:
            existing = {**json.loads(row["data"]), "stock": row["stock"], "status": row["status"]}
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        new_slug = request.form.get("slug", "").strip().lower().replace(" ", "-")
        if not name or not new_slug:
            flash("Product name and slug are required.", "error")
        else:
            badges = request.form.getlist("badges") or ["New"]
            uploads = request.files.getlist("images")
            image_name = request.form.get(
                "image", "photo_2_2026-06-08_18-19-49.webp"
            )
            saved_images = []
            for upload in uploads:
                if not upload or not upload.filename:
                    continue
                filename = secure_filename(upload.filename)
                upload.save(
                    Path(current_app.root_path)
                    / "Aluye Naturals Images"
                    / filename
                )
                saved_images.append(filename)
            if saved_images:
                image_name = saved_images[0]
            try:
                price = float(request.form.get("price") or 0)
                compare_at = float(request.form.get("compare_at") or 0)
                stock = max(0, int(request.form.get("stock") or 0))
                rating = min(5, max(0, float(request.form.get("rating") or 4.8)))
                reviews = max(0, int(request.form.get("reviews") or 0))
            except ValueError:
                flash("Price, stock, rating and reviews must be valid numbers.", "error")
                return render_template(
                    "admin/product_form.html",
                    admin_section="products",
                    product=request.form,
                    categories=CATEGORIES_REF,
                )
            product = {
                "slug": new_slug,
                "name": name,
                "segment": request.form.get("category", CATEGORIES_REF[0]),
                "category": request.form.get("subcategory", "Natural Care"),
                "benefit": request.form.get("short_description", "").strip(),
                "description": request.form.get("description", "").strip(),
                "price": price,
                "compare_at": compare_at,
                "size": request.form.get("size", ""),
                "badge": badges[0],
                "tags": badges,
                "image": image_name,
                "images": saved_images
                or (existing.get("images", []) if existing else []),
                "ingredients": [x.strip() for x in request.form.get("ingredients", "").split(",") if x.strip()],
                "best_for": request.form.get("best_for", ""),
                "how_to": request.form.get("how_to", ""),
                "rating": rating,
                "reviews": reviews,
                "is_new": "New" in badges,
            }
            status = request.form.get("status", "active")
            if slug and slug != new_slug:
                db.execute("DELETE FROM products WHERE slug=?", (slug,))
                PRODUCTS_REF[:] = [p for p in PRODUCTS_REF if p["slug"] != slug]
            db.execute(
                """INSERT INTO products(slug,data,stock,status,updated_at) VALUES(?,?,?,?,?)
                   ON CONFLICT(slug) DO UPDATE SET data=excluded.data,stock=excluded.stock,
                   status=excluded.status,updated_at=excluded.updated_at""",
                (new_slug, json.dumps(product), stock, status, datetime.now().isoformat(timespec="minutes")),
            )
            if existing is not None and existing.get("stock") != stock:
                log_stock_change(
                    new_slug, stock - existing.get("stock", 0), "admin_edit", stock,
                    reference=session.get("admin_username", "admin"),
                )
            db.commit()
            reload_products_from_db()
            if stock < 5:
                add_notification(
                    "stock",
                    "Low stock alert",
                    f"{name} has {stock} units remaining.",
                )
            record_activity(f"Saved product: {name}")
            flash("Product saved and storefront catalogue updated.", "success")
            return redirect(url_for("admin.products"))
    return render_template(
        "admin/product_form.html",
        admin_section="products",
        product=existing or {},
        categories=CATEGORIES_REF,
    )


@admin_bp.post("/products/<slug>/delete")
def product_delete(slug):
    get_db().execute("DELETE FROM products WHERE slug=?", (slug,))
    get_db().commit()
    reload_products_from_db()
    record_activity(f"Deleted product: {slug}")
    flash("Product deleted.", "success")
    return redirect(url_for("admin.products"))


@admin_bp.get("/orders")
def orders():
    rows = get_db().execute("SELECT * FROM orders ORDER BY created_at DESC").fetchall()
    return render_template("admin/orders.html", admin_section="orders", orders=rows)


@admin_bp.route("/orders/<int:order_id>", methods=["GET", "POST"])
def order_detail(order_id):
    db = get_db()
    if request.method == "POST":
        old_order = db.execute(
            "SELECT order_number,status,items,customer_name,email FROM orders WHERE id=?", (order_id,)
        ).fetchone()
        new_status = request.form.get("status")
        tracking = request.form.get("tracking", "")
        if new_status == "Cancelled" and old_order and old_order["status"] != "Cancelled":
            restore_stock(json.loads(old_order["items"]), reference=old_order["order_number"])
        db.execute(
            "UPDATE orders SET status=?,tracking=?,updated_at=? WHERE id=?",
            (
                new_status,
                tracking,
                datetime.now().isoformat(timespec="minutes"),
                order_id,
            ),
        )
        db.commit()
        if old_order and old_order["status"] != new_status:
            add_notification(
                "order",
                "Order status updated",
                f"{old_order['order_number']} is now {new_status}.",
            )
            if new_status in ("Shipped", "Delivered"):
                send_order_status_email(old_order, new_status, tracking)
        record_activity(f"Updated order #{order_id}")
        flash("Order updated.", "success")
    order = db.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
    return render_template(
        "admin/order_detail.html",
        admin_section="orders",
        order=order,
        order_items=json.loads(order["items"]),
    )


@admin_bp.route("/messages", methods=["GET", "POST"])
def messages():
    db = get_db()
    if request.method == "POST":
        message_id = request.form.get("message_id")
        action = request.form.get("action")
        if action == "delete":
            db.execute("DELETE FROM messages WHERE id=?", (message_id,))
        else:
            db.execute("UPDATE messages SET status=? WHERE id=?", (action, message_id))
        db.commit()
        flash("Inbox updated.", "success")
    rows = db.execute("SELECT * FROM messages ORDER BY created_at DESC").fetchall()
    return render_template("admin/messages.html", admin_section="messages", messages=rows)


@admin_bp.route("/messages/<int:message_id>", methods=["GET", "POST"])
def message_detail(message_id):
    db = get_db()
    msg = db.execute("SELECT * FROM messages WHERE id=?", (message_id,)).fetchone()
    if not msg:
        flash("Message not found.", "error")
        return redirect(url_for("admin.messages"))
    if msg["status"] == "unread":
        db.execute("UPDATE messages SET status='read' WHERE id=?", (message_id,))
        db.commit()

    if request.method == "POST":
        action = request.form.get("action", "send")
        reply_text = request.form.get("reply_text", "").strip()

        if action == "discard_draft":
            db.execute("DELETE FROM message_drafts WHERE message_id=?", (message_id,))
            db.commit()
            flash("Draft discarded.", "success")
            return redirect(url_for("admin.message_detail", message_id=message_id))

        if action == "save_draft" and reply_text:
            db.execute(
                """INSERT INTO message_drafts(message_id, draft_text, updated_at) VALUES(?,?,?)
                   ON CONFLICT(message_id) DO UPDATE SET draft_text=excluded.draft_text, updated_at=excluded.updated_at""",
                (message_id, reply_text, datetime.now().isoformat(timespec="minutes")),
            )
            db.commit()
            flash("Draft saved.", "success")
            return redirect(url_for("admin.message_detail", message_id=message_id))

        if action == "send" and reply_text:
            email_html = render_template(
                "emails/reply.html",
                reply_text=reply_text,
                customer_name=msg["name"],
                site_url=current_app.config.get("SITE_URL", ""),
            )
            sent, mail_error = send_mail(
                subject=f"Re: {msg['subject']}",
                recipients=[msg["email"]],
                html=email_html,
            )

            db.execute(
                "INSERT INTO message_replies(message_id, reply_text, replied_by, created_at) VALUES(?,?,?,?)",
                (message_id, reply_text, session.get("admin_username", "admin"), datetime.now().isoformat(timespec="minutes")),
            )
            db.execute("UPDATE messages SET status='replied' WHERE id=?", (message_id,))
            db.execute("DELETE FROM message_drafts WHERE message_id=?", (message_id,))
            db.commit()
            record_activity(f"Replied to message #{message_id}")
            if sent:
                flash(f"Reply sent to {msg['email']} ✓", "success")
            else:
                flash(f"Reply saved but email could not be sent: {mail_error}. Check SMTP settings in Global Settings → Integrations.", "error")
            return redirect(url_for("admin.message_detail", message_id=message_id))

    replies = db.execute(
        "SELECT * FROM message_replies WHERE message_id=? ORDER BY created_at", (message_id,)
    ).fetchall()
    draft = db.execute(
        "SELECT * FROM message_drafts WHERE message_id=?", (message_id,)
    ).fetchone()
    return render_template(
        "admin/message_detail.html",
        admin_section="messages",
        msg=msg,
        replies=replies,
        draft=draft,
    )


@admin_bp.route("/settings/test-email", methods=["POST"])
def test_email():
    settings = load_setting("settings", {}) or {}
    recipient = settings.get("mail_username") or current_app.config.get("MAIL_USERNAME", "")
    if not recipient:
        flash("No SMTP username configured. Add one in Global Settings → Integrations.", "error")
    else:
        sent, error = send_mail(
            subject="Aluyè Naturals — Test Email",
            recipients=[recipient],
            html="<p>This is a test email from your Aluyè Naturals admin panel. Email is configured correctly.</p>",
        )
        if sent:
            flash(f"Test email sent to {recipient} ✓", "success")
        else:
            flash(f"Email failed: {error}", "error")
    return redirect(url_for("admin.global_settings") + "?tab=integrations")


@admin_bp.post("/notifications/read")
def notifications_read():
    get_db().execute("UPDATE notifications SET is_read=1")
    get_db().commit()
    flash("Notifications marked as read.", "success")
    return redirect(url_for("admin.notifications"))


@admin_bp.get("/notifications")
def notifications():
    rows = get_db().execute(
        "SELECT * FROM notifications WHERE archived=0 ORDER BY created_at DESC"
    ).fetchall()
    return render_template(
        "admin/notifications.html",
        admin_section="notifications",
        notifications=rows,
    )


def _notification_related_url(row):
    if row["related_type"] == "order" and row["related_id"]:
        return url_for("admin.order_detail", order_id=row["related_id"])
    if row["related_type"] == "message" and row["related_id"]:
        return url_for("admin.message_detail", message_id=row["related_id"])
    return None


@admin_bp.get("/notifications/<int:notification_id>")
def notification_detail(notification_id):
    db = get_db()
    row = db.execute("SELECT * FROM notifications WHERE id=?", (notification_id,)).fetchone()
    if not row:
        abort(404)
    if not row["is_read"]:
        db.execute("UPDATE notifications SET is_read=1 WHERE id=?", (notification_id,))
        db.commit()
        row = db.execute("SELECT * FROM notifications WHERE id=?", (notification_id,)).fetchone()
    return render_template(
        "admin/notification_detail.html",
        admin_section="notifications",
        notification=row,
        related_url=_notification_related_url(row),
    )


@admin_bp.post("/notifications/<int:notification_id>/archive")
def notification_archive(notification_id):
    get_db().execute("UPDATE notifications SET archived=1 WHERE id=?", (notification_id,))
    get_db().commit()
    flash("Notification archived.", "success")
    return redirect(url_for("admin.notifications"))


@admin_bp.post("/notifications/<int:notification_id>/delete")
def notification_delete(notification_id):
    get_db().execute("DELETE FROM notifications WHERE id=?", (notification_id,))
    get_db().commit()
    flash("Notification deleted.", "success")
    return redirect(url_for("admin.notifications"))


@admin_bp.route("/homepage", methods=["GET", "POST"])
def homepage():
    defaults = {
        "announcement_1": "Delivering across Canada",
        "announcement_2": "Small-batch care, rooted in nature",
        "announcement_3": "New arrivals every month — Shop now",
        "hero_headline": "Shea care, made beautifully modern.",
        "hero_subheadline": "Discover small-batch care rooted in West African ingredients.",
        "hero_button": "Shop skin care",
        "hero_link": "/shop?category=Skin+Care",
        "new_arrivals": True,
        "best_sellers": True,
        "brand_story": True,
        "ingredients": True,
        "journal": True,
        "signup_heading": "Get 15% off your first ritual",
        "signup_subheading": "Join for product launches, ingredient guides and members-only offers.",
        "category_order": "Skin Care,Oil,Hair,Beards,African Black Soap",
        "category_skin_care": True,
        "category_oil": True,
        "category_hair": True,
        "category_beards": True,
        "category_african_black_soap": True,
    }
    if request.method == "POST":
        data = {key: request.form.get(key, "") for key in defaults}
        for key in (
            "new_arrivals",
            "best_sellers",
            "brand_story",
            "ingredients",
            "journal",
            "category_skin_care",
            "category_oil",
            "category_hair",
            "category_beards",
            "category_african_black_soap",
        ):
            data[key] = key in request.form
        save_setting("homepage", data)
        record_activity("Updated homepage content")
        flash("Homepage settings saved.", "success")
        return redirect(url_for("admin.homepage"))
    return render_template(
        "admin/homepage.html",
        admin_section="homepage",
        settings={**defaults, **(load_setting("homepage", {}) or {})},
    )


SETTINGS_TABS = [
    ("general", "General"),
    ("branding", "Branding"),
    ("contact", "Contact"),
    ("social", "Social Media"),
    ("homepage", "Homepage"),
    ("store", "Store"),
    ("seo", "SEO"),
    ("newsletter", "Newsletter"),
    ("messages", "Automated Messages"),
    ("footer", "Footer"),
    ("integrations", "Integrations"),
]

SETTINGS_DEFAULTS = {
    "store_name": "Aluyè Naturals",
    "tagline": "Body · Mind · Soul",
    "store_status": "live",
    "base_currency": "CAD",
    "signup_heading": "Get 15% off your first ritual",
    "signup_subheading": "Join for product launches, ingredient guides and members-only offers.",
    "copyright_text": "© 2026 Aluyè Naturals. Body. Mind. Soul.",
    "footer_description": "Natural skin, hair, body and beard care rooted in West African ingredients and everyday ritual.",
    "instagram": "https://www.instagram.com/aluye_naturals",
    "instagram_url": "https://www.instagram.com/aluye_naturals",
    "tiktok": "https://www.tiktok.com/@aluye_naturals?_r=1&_t=ZS-97jHiLTSc6u",
    "tiktok_url": "https://www.tiktok.com/@aluye_naturals?_r=1&_t=ZS-97jHiLTSc6u",
    "meta_title": "Aluyè Naturals | Premium Organic Skincare Rooted in West Africa",
    "meta_description": "Aluyè Naturals — Organic skincare rooted in West African heritage. Pure shea butter, authentic African black soap, botanical oils and care. Body. Mind. Soul.",
    "response_time": "We aim to reply within two business days.",
    "returns_window": "30",
    "gift_wrap_price": "3",
    "low_stock_threshold": "5",
    "welcome_email_subject": "Welcome to the ritual 🌿",
    "welcome_discount_code": "RITUAL15",
    "shipped_email_subject": "Your Aluyè Naturals order has shipped 🌿",
    "shipped_email_message": "Your order is on its way to you.",
    "delivered_email_subject": "Your Aluyè Naturals order has been delivered 🌿",
    "delivered_email_message": "Your order has been delivered. We hope you love your ritual.",
    "inquiry_autoresponse_subject": "We've received your message 🌿",
    "inquiry_autoresponse_message": "Thank you for reaching out to Aluyè Naturals. We've received your message and will reply within two business days.",
    "abandoned_cart_subject": "You left something in your cart 🌿",
    "abandoned_cart_message": "Your ritual is still waiting for you. Complete your order before it sells out.",
    "abandoned_cart_delay_hours": "24",
}


@admin_bp.route("/global-settings", methods=["GET", "POST"])
def global_settings():
    if session.get("admin_role") != "Super Admin":
        flash("Only a Super Admin can access settings.", "error")
        return redirect(url_for("admin.dashboard"))

    if request.method == "POST":
        tab = request.form.get("tab", "general")
        settings = load_setting("settings", {}) or {}
        homepage = load_setting("homepage", {}) or {}
        target = homepage if tab == "homepage" else settings
        required_by_tab = {
            "general": ["store_name"],
            "contact": ["contact_email"],
        }
        missing = [
            field
            for field in required_by_tab.get(tab, [])
            if not request.form.get(field, "").strip()
        ]
        if missing:
            flash("Please complete all required fields before saving.", "error")
            return redirect(url_for("admin.global_settings") + f"?tab={tab}")
        for key, value in request.form.items():
            if key == "tab":
                continue
            target[key] = value
        checkbox_fields = [
            "new_arrivals", "best_sellers", "brand_story", "ingredients", "journal",
            "welcome_email_enabled", "gift_wrap_enabled",
            "shipped_email_enabled", "delivered_email_enabled",
            "inquiry_autoresponse_enabled", "abandoned_cart_enabled",
        ]
        for field in checkbox_fields:
            if tab in ("homepage", "store", "newsletter", "messages"):
                target[field] = field in request.form
        if tab == "integrations":
            target["paypal_sandbox"] = "paypal_sandbox" in request.form
            mail_password = request.form.get("mail_password", "").strip()
            if mail_password:
                save_env_secret("MAIL_PASSWORD", mail_password)
            target["mail_password"] = ""
            target["mail_configured"] = bool(mail_password or settings.get("mail_configured"))
            secret_fields = ("stripe_secret", "paypal_secret", "flutterwave_secret", "paystack_secret")
            for field in secret_fields:
                secret = request.form.get(field, "").strip()
                provider = field.removesuffix("_secret")
                if secret:
                    save_env_secret(field.upper(), secret)
                target[field] = ""
                target[f"{provider}_configured"] = bool(
                    secret or settings.get(f"{provider}_configured")
                )
        if tab == "homepage":
            save_setting("homepage", homepage)
        else:
            save_setting("settings", settings)
        record_activity(f"Updated {tab} settings")
        flash("Settings saved ✓", "success")
        return redirect(url_for("admin.global_settings") + f"?tab={tab}")

    all_settings = {**SETTINGS_DEFAULTS}
    all_settings.update(load_setting("settings", {}) or {})
    all_settings.update(load_setting("homepage", {}) or {})

    return render_template(
        "admin/global_settings.html",
        admin_section="settings",
        tabs=SETTINGS_TABS,
        s=all_settings,
        defaults=SETTINGS_DEFAULTS,
    )


@admin_bp.route("/shipping", methods=["GET", "POST"])
def shipping():
    db = get_db()
    if request.method == "POST":
        if request.form.get("form_type") == "settings":
            settings = load_setting("settings", {}) or {}
            settings["shipping_pickup_enabled"] = "shipping_pickup_enabled" in request.form
            settings["shipping_manual_quote_enabled"] = "shipping_manual_quote_enabled" in request.form
            save_setting("settings", settings)
            flash("Shipping settings updated.", "success")
        elif request.form.get("form_type") == "distance":
            settings = load_setting("settings", {}) or {}
            settings["distance_shipping_enabled"] = "distance_shipping_enabled" in request.form
            settings["shipping_free_delivery_enabled"] = "shipping_free_delivery_enabled" in request.form
            settings["shipping_origin_address"] = request.form.get("shipping_origin_address", "").strip() or "Toronto, Ontario, Canada"
            settings["shipping_base_fee"] = request.form.get("shipping_base_fee", "0")
            settings["shipping_per_km_rate"] = request.form.get("shipping_per_km_rate", "0")
            settings["shipping_max_distance_km"] = request.form.get("shipping_max_distance_km", "0")
            settings["shipping_free_delivery_minimum"] = request.form.get("shipping_free_delivery_minimum", "0")
            google_maps_key = request.form.get("google_maps_key", "").strip()
            if google_maps_key:
                save_env_secret("GOOGLE_MAPS_API_KEY", google_maps_key)
            settings["google_maps_configured"] = bool(google_maps_key or settings.get("google_maps_configured"))
            save_setting("settings", settings)
            record_activity("Updated distance-based shipping settings")
            flash("Distance-based shipping settings updated.", "success")
        elif request.form.get("delete"):
            db.execute("DELETE FROM shipping_zones WHERE id=?", (request.form["delete"],))
            db.commit()
            flash("Shipping zone deleted.", "success")
        else:
            name = request.form.get("name", "").strip()
            if not name:
                flash("Zone name is required.", "error")
            else:
                db.execute(
                    "INSERT INTO shipping_zones(name,rate,threshold,delivery_days,postal_prefixes,enabled) VALUES(?,?,?,?,?,?)",
                    (
                        name,
                        float(request.form.get("rate") or 0),
                        0,
                        request.form.get("delivery_days"),
                        request.form.get("postal_prefixes", "").strip().upper(),
                        1,
                    ),
                )
                db.commit()
                flash("Shipping zone added.", "success")
        return redirect(url_for("admin.shipping"))
    settings = load_setting("settings", {}) or {}
    return render_template(
        "admin/shipping.html",
        admin_section="shipping",
        zones=db.execute("SELECT * FROM shipping_zones ORDER BY name").fetchall(),
        s=settings,
    )


@admin_bp.route("/discounts", methods=["GET", "POST"])
def discounts():
    db = get_db()
    if request.method == "POST":
        if request.form.get("delete"):
            db.execute("DELETE FROM discounts WHERE id=?", (request.form["delete"],))
        else:
            db.execute(
                """INSERT INTO discounts(code,type,value,minimum,expiry,usage_limit,enabled)
                   VALUES(?,?,?,?,?,?,1)""",
                (
                    request.form.get("code", "").upper(),
                    request.form.get("type"),
                    float(request.form.get("value") or 0),
                    float(request.form.get("minimum") or 0),
                    request.form.get("expiry"),
                    int(request.form.get("usage_limit") or 0),
                ),
            )
        db.commit()
        flash("Discount codes updated.", "success")
    return render_template(
        "admin/discounts.html",
        admin_section="discounts",
        discounts=db.execute("SELECT * FROM discounts ORDER BY id DESC").fetchall(),
    )


@admin_bp.route("/journal", methods=["GET", "POST"])
def journal():
    db = get_db()
    if request.method == "POST":
        if request.form.get("delete"):
            post_id = request.form["delete"]
            row = db.execute(
                "SELECT slug FROM blog_posts WHERE id=?", (post_id,)
            ).fetchone()
            db.execute("DELETE FROM blog_posts WHERE id=?", (post_id,))
            if row:
                BLOG_POSTS_REF[:] = [
                    post for post in BLOG_POSTS_REF if post["slug"] != row["slug"]
                ]
        else:
            title = request.form.get("title", "").strip()
            slug = request.form.get("slug", "").strip() or title.lower().replace(" ", "-")
            db.execute(
                """INSERT INTO blog_posts(slug,title,category,body,status,created_at)
                   VALUES(?,?,?,?,?,?)""",
                (
                    slug,
                    title,
                    request.form.get("category"),
                    request.form.get("body"),
                    request.form.get("status"),
                    datetime.now().isoformat(timespec="minutes"),
                ),
            )
            if request.form.get("status") == "published":
                BLOG_POSTS_REF[:] = [
                    post for post in BLOG_POSTS_REF if post["slug"] != slug
                ]
                BLOG_POSTS_REF.append(
                    {
                        "slug": slug,
                        "tag": request.form.get("category"),
                        "title": title,
                        "excerpt": request.form.get("body", "")[:160],
                        "body": [
                            paragraph.strip()
                            for paragraph in request.form.get("body", "").split("\n")
                            if paragraph.strip()
                        ],
                    }
                )
        db.commit()
        reload_blog_posts_from_db()
        flash("Journal updated.", "success")
    return render_template(
        "admin/journal.html",
        admin_section="journal",
        posts=db.execute("SELECT * FROM blog_posts ORDER BY created_at DESC").fetchall(),
    )


@admin_bp.get("/analytics")
def analytics():
    db = get_db()
    pages = db.execute("SELECT * FROM analytics ORDER BY views DESC").fetchall()
    products = db.execute(
        "SELECT * FROM product_events ORDER BY views DESC LIMIT 5"
    ).fetchall()
    orders = db.execute("SELECT COUNT(*) c FROM orders").fetchone()["c"]
    visits = sum(row["views"] for row in pages)
    return render_template(
        "admin/analytics.html",
        admin_section="analytics",
        pages=pages,
        product_events=products,
        visits=visits,
        conversion=round((orders / visits * 100), 2) if visits else 0,
        chart=[32, 38, 41, 39, 47, 55, 61, 58, 70, 76, 81, 94],
    )


@admin_bp.get("/analytics/export.csv")
def analytics_export():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Page", "Views"])
    writer.writerows(
        get_db().execute("SELECT path,views FROM analytics ORDER BY views DESC").fetchall()
    )
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=aluye-analytics.csv"},
    )


@admin_bp.route("/reviews", methods=["GET", "POST"])
def reviews_admin():
    db = get_db()
    if request.method == "POST":
        review_id = request.form.get("review_id")
        action = request.form.get("action")
        if action == "approve":
            db.execute("UPDATE reviews SET status='approved' WHERE id=?", (review_id,))
        elif action == "reject":
            db.execute("UPDATE reviews SET status='rejected' WHERE id=?", (review_id,))
        elif action == "delete":
            db.execute("DELETE FROM reviews WHERE id=?", (review_id,))
        db.commit()
        record_activity(f"Review {action}: #{review_id}")
        flash("Review updated.", "success")
    rows = db.execute("SELECT * FROM reviews ORDER BY created_at DESC").fetchall()
    return render_template(
        "admin/reviews.html",
        admin_section="reviews_admin",
        reviews=rows,
    )


@admin_bp.get("/issues")
def issues_admin():
    return render_template(
        "admin/issues.html",
        admin_section="issues_admin",
        issues=SITE_ISSUES,
    )


@admin_bp.get("/subscribers")
def subscribers_admin():
    rows = get_db().execute(
        "SELECT * FROM subscribers ORDER BY created_at DESC"
    ).fetchall()
    return render_template(
        "admin/subscribers.html",
        admin_section="subscribers_admin",
        subscribers=rows,
    )


@admin_bp.get("/subscribers/export.csv")
def subscribers_export():
    rows = get_db().execute(
        "SELECT email, source, created_at FROM subscribers ORDER BY created_at DESC"
    ).fetchall()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Email", "Source", "Subscribed", "Status"])
    writer.writerows([(row["email"], row["source"] or "website", row["created_at"], "Active") for row in rows])
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=aluye-subscribers.csv"},
    )


@admin_bp.route("/abandoned", methods=["GET", "POST"])
def abandoned_admin():
    db = get_db()
    if request.method == "POST":
        cart_id = request.form.get("cart_id")
        if request.form.get("action") == "delete":
            db.execute("DELETE FROM abandoned_carts WHERE id=?", (cart_id,))
        db.commit()
        flash("Updated.", "success")
    rows = db.execute(
        "SELECT * FROM abandoned_carts ORDER BY created_at DESC"
    ).fetchall()
    return render_template(
        "admin/abandoned.html",
        admin_section="abandoned_admin",
        carts=rows,
    )


@admin_bp.route("/returns", methods=["GET", "POST"])
def returns_admin():
    db = get_db()
    if request.method == "POST":
        req_id = request.form.get("return_id")
        new_status = request.form.get("status")
        note = request.form.get("admin_note", "")
        if req_id and new_status:
            db.execute(
                "UPDATE return_requests SET status=?, admin_note=? WHERE id=?",
                (new_status, note, req_id),
            )
            db.commit()
            record_activity(f"Return request #{req_id} → {new_status}")
            flash("Return request updated.", "success")
    rows = db.execute(
        "SELECT * FROM return_requests ORDER BY created_at DESC"
    ).fetchall()
    return render_template(
        "admin/returns.html",
        admin_section="returns_admin",
        returns=rows,
    )


@admin_bp.route("/account", methods=["GET", "POST"])
def account():
    db = get_db()
    if request.method == "POST":
        if request.form.get("new_user"):
            db.execute(
                "INSERT INTO admin_users(username,name,email,password_hash,role) VALUES(?,?,?,?,?)",
                (
                    request.form.get("username"),
                    request.form.get("name"),
                    request.form.get("email"),
                    generate_password_hash(request.form.get("password")),
                    request.form.get("role"),
                ),
            )
        elif request.form.get("password"):
            db.execute(
                "UPDATE admin_users SET password_hash=? WHERE id=?",
                (generate_password_hash(request.form["password"]), session["admin_user_id"]),
            )
        db.commit()
        flash("Account settings saved.", "success")
    return render_template(
        "admin/account.html",
        admin_section="account",
        users=db.execute("SELECT * FROM admin_users ORDER BY id").fetchall(),
        activity=db.execute("SELECT * FROM activity ORDER BY id DESC LIMIT 20").fetchall(),
    )
