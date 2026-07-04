import gzip
import json
import os
import re
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

from flask import (
    Flask,
    abort,
    flash,
    make_response,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from catalog import (
    BLOG_POSTS as CATALOG_BLOG_POSTS,
    CATEGORIES as CATALOG_CATEGORIES,
    HERO_SLIDES as CATALOG_HERO_SLIDES,
    INGREDIENTS as CATALOG_INGREDIENTS,
    PRODUCTS as CATALOG_PRODUCTS,
)
from admin import (
    deduct_stock,
    init_admin,
    load_setting,
    record_page_view,
    record_product_event,
    save_contact_message,
    save_order,
)


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_META_TITLE = "Aluyè Naturals | Premium Organic Skincare Rooted in West Africa"
DEFAULT_META_DESCRIPTION = (
    "Aluyè Naturals — Organic skincare rooted in West African heritage. Pure shea "
    "butter, authentic African black soap, botanical oils and care. Body. Mind. Soul."
)


def has_broken_translation(value):
    if not isinstance(value, str):
        return False
    lowered = value.lower()
    return "trans-" in value or "welcome to wordpress" in lowered or "this is your first post" in lowered


def clean_meta(value, fallback):
    if not value or has_broken_translation(value):
        return fallback
    return " ".join(str(value).split())


def get_meta_override(key, fallback):
    """Admin-configured SEO override (Global Settings -> SEO), falling back to the
    on-brand default if unset or corrupted."""
    settings = load_setting("settings", {}) or {}
    return clean_meta(settings.get(key), fallback)


def create_app(test_config=None):
    app = Flask(__name__)
    mail_user = os.environ.get("MAIL_USERNAME", "")
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-change-me"),
        SITE_URL=os.environ.get("SITE_URL", "http://127.0.0.1:5000").rstrip("/"),
        MAX_CONTENT_LENGTH=16 * 1024 * 1024,
        MAIL_SERVER=os.environ.get("MAIL_SERVER", "smtp.gmail.com"),
        MAIL_PORT=int(os.environ.get("MAIL_PORT", 587)),
        MAIL_USE_TLS=True,
        MAIL_USERNAME=mail_user,
        MAIL_PASSWORD=os.environ.get("MAIL_PASSWORD", ""),
        MAIL_DEFAULT_SENDER=mail_user or "noreply@aluyenaturals.com",
        MAIL_SUPPRESS_SEND=not mail_user,
    )
    if test_config:
        app.config.update(test_config)
    init_admin(app, PRODUCTS, CATEGORIES, BLOG_POSTS)

    @app.before_request
    def track_storefront_visit():
        if request.method == "GET" and not request.path.startswith(
            ("/admin", "/static", "/media", "/health")
        ):
            if request.args.get("preview") == "aluye2026":
                session["preview_mode"] = True
            settings = load_setting("settings", {}) or {}
            if settings.get("store_status", "").lower() == "maintenance" and not session.get(
                "preview_mode"
            ):
                return render_template(
                    "maintenance.html",
                    message=settings.get("maintenance_message")
                    or "Aluyè Naturals is currently undergoing some improvements. We will be back very soon.",
                ), 503
            record_page_view(request.path)

    @app.context_processor
    def inject_site_metadata():
        _, cart_subtotal = cart_summary()
        site_settings = load_setting("settings", {}) or {}
        homepage_settings = load_setting("homepage", {}) or {}
        social_defaults = {
            "instagram": "https://www.instagram.com/aluye_naturals",
            "instagram_url": "https://www.instagram.com/aluye_naturals",
            "tiktok": "https://www.tiktok.com/@aluye_naturals?_r=1&_t=ZS-97jHiLTSc6u",
            "tiktok_url": "https://www.tiktok.com/@aluye_naturals?_r=1&_t=ZS-97jHiLTSc6u",
        }
        for key, value in social_defaults.items():
            if not site_settings.get(key) or has_broken_translation(site_settings.get(key)):
                site_settings[key] = value

        if not site_settings.get("contact_email") or has_broken_translation(
            site_settings.get("contact_email")
        ):
            site_settings["contact_email"] = "erica@aluyenaturals.com"

        def get_setting(key, default=""):
            aliases = {
                "instagram_url": "instagram",
                "tiktok_url": "tiktok",
                "facebook_url": "facebook",
                "pinterest_url": "pinterest",
            }
            value = site_settings.get(key)
            if not value and key in aliases:
                value = site_settings.get(aliases[key])
            if not value and key in social_defaults:
                value = social_defaults[key]
            return "" if has_broken_translation(value) else (value or default)

        return {
            "site_name": clean_meta(site_settings.get("store_name"), "Aluyè Naturals"),
            "site_url": app.config["SITE_URL"],
            "cart_count": sum(session.get("cart", {}).values()),
            "cart_subtotal": cart_subtotal,
            "breadcrumbs": build_breadcrumbs(),
            "site_settings": site_settings,
            "homepage_settings": homepage_settings,
            "current_year": datetime.now().year,
            "default_meta_title": get_meta_override("meta_title", DEFAULT_META_TITLE),
            "default_meta_description": get_meta_override(
                "meta_description", DEFAULT_META_DESCRIPTION
            ),
            "get_setting": get_setting,
        }

    @app.get("/")
    def home():
        category_images = {
            "Skin Care": "photo_2_2026-06-08_18-19-49.webp",
            "Oil": "photo_2026-06-09_11-04-11.webp",
            "Men": "photo_7_2026-06-08_18-19-49.webp",
            "Hair": "photo_4_2026-06-05_22-40-06.webp",
            "Beards": "photo_2026-06-09_11-04-16.webp",
            "African Black Soap": "photo_2026-06-09_11-04-04.webp",
        }
        homepage_settings = load_setting("homepage", {}) or {}
        category_order = [
            item.strip()
            for item in homepage_settings.get(
                "category_order", ",".join(category_images)
            ).split(",")
            if item.strip() in category_images
        ]
        category_order.extend(
            category for category in category_images if category not in category_order
        )
        homepage_categories = [
            (category, category_images[category])
            for category in category_order
            if homepage_settings.get(
                f"category_{category.lower().replace(' ', '_')}", True
            )
        ]
        canonical_url = absolute_url("/")
        hero_image_url = absolute_url(
            url_for(
                "media",
                collection="hero",
                filename="aluye-chlorophyll-hero.webp",
            )
        )
        logo_url = absolute_url(
            url_for(
                "media",
                collection="products",
                filename="Aluye Naturals Logo.jpg",
            )
        )
        seo = {
            "title": get_meta_override("meta_title", DEFAULT_META_TITLE),
            "description": get_meta_override(
                "meta_description",
                "Aluyè Naturals — Small-batch organic skincare, body butter, African "
                "black soap and botanical oils rooted in West African heritage ingredients. "
                "Delivered across Canada.",
            ),
            "canonical_url": canonical_url,
            "image_url": hero_image_url,
            "image_alt": "Aluyè Naturals chlorophyll whipped shea butter on natural stone",
            "robots": "index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1",
        }
        structured_data = [
            {
                "@context": "https://schema.org",
                "@type": "OnlineStore",
                "@id": f"{canonical_url}#store",
                "name": "Aluyè Naturals",
                "alternateName": "Aluye Naturals",
                "url": canonical_url,
                "logo": logo_url,
                "image": hero_image_url,
                "description": seo["description"],
                "slogan": "Body. Mind. Soul.",
                "knowsAbout": [
                    "Unrefined shea butter",
                    "African black soap",
                    "Natural skin care",
                    "Natural hair care",
                    "Beard care",
                ],
            },
            {
                "@context": "https://schema.org",
                "@type": "WebSite",
                "@id": f"{canonical_url}#website",
                "url": canonical_url,
                "name": "Aluyè Naturals",
                "alternateName": "Aluye Naturals",
                "publisher": {"@id": f"{canonical_url}#store"},
                "inLanguage": "en",
            },
        ]
        return render_template(
            "home.html",
            products=PRODUCTS,
            product_segments=[
                (category, [product for product in PRODUCTS if product["segment"] == category])
                for category in CATEGORIES
            ],
            rituals=RITUALS,
            ingredients=INGREDIENTS,
            testimonials=TESTIMONIALS,
            journal=JOURNAL,
            hero_slides=HERO_SLIDES,
            new_arrivals=[product for product in PRODUCTS if product["is_new"]][:3],
            best_sellers=[
                product for product in PRODUCTS if "Best Seller" in product["tags"]
            ][:3],
            homepage_categories=homepage_categories,
            seo=seo,
            structured_data=structured_data,
        )

    @app.get("/media/<collection>/<path:filename>")
    def media(collection, filename):
        folders = {
            "products": BASE_DIR / "Aluye Naturals Images",
            "hero": BASE_DIR / "Aluye Naturals Hero",
        }
        folder = folders.get(collection)
        if folder is None:
            abort(404)
        return send_from_directory(folder, filename)

    @app.get("/health")
    def health():
        return {"status": "ok", "service": "aluye-naturals"}

    @app.get("/api/search")
    def api_search():
        query = request.args.get("q", "").strip()
        if not query:
            return {"results": [
                {
                    "slug": p["slug"],
                    "name": p["name"],
                    "category": p.get("segment", p.get("category", "")),
                    "price": p["price"],
                    "image": p["image"],
                }
                for p in PRODUCTS
            ]}
        if len(query) < 2:
            return {"results": []}
        needle = query.casefold()
        results = [
            {
                "slug": p["slug"],
                "name": p["name"],
                "category": p.get("segment", p.get("category", "")),
                "price": p["price"],
                "image": p["image"],
            }
            for p in PRODUCTS
            if needle
            in " ".join(
                [
                    p["name"],
                    p.get("category", ""),
                    p.get("segment", ""),
                    p.get("benefit", ""),
                    " ".join(p.get("ingredients", [])),
                ]
            ).casefold()
        ]
        return {"results": results[:10]}

    @app.post("/api/subscribe")
    def api_subscribe():
        from admin import get_db, add_notification, send_welcome_email

        payload = request.get_json(silent=True) or {}
        email = (payload.get("email") or request.form.get("email", "")).strip()
        source = (payload.get("source") or request.form.get("source", "website")).strip()

        email_regex = r"^[^\s@]+@[^\s@]+\.[^\s@]+$"
        if not email or not re.match(email_regex, email):
            return {"ok": False, "status": "invalid_email"}, 400

        db = get_db()
        existing = db.execute(
            "SELECT 1 FROM subscribers WHERE email=?", (email,)
        ).fetchone()
        if existing:
            return {"ok": True, "status": "already_subscribed"}

        db.execute(
            "INSERT INTO subscribers(email, created_at, source) VALUES(?, ?, ?)",
            (email, datetime.now().isoformat(timespec="minutes"), source),
        )
        db.commit()
        add_notification("subscriber", "New subscriber", email)

        try:
            send_welcome_email(email, source=source)
        except Exception as exc:
            print(f"Welcome email error for {email}: {exc}")

        return {
            "ok": True,
            "status": "subscribed",
            "discount_code": "RITUAL10" if source == "exit_popup" else "RITUAL15",
        }

    @app.get("/unsubscribe")
    def unsubscribe():
        from admin import get_db

        email = request.args.get("email", "").strip()
        if email:
            db = get_db()
            db.execute("DELETE FROM subscribers WHERE email=?", (email,))
            db.commit()
        return render_template("unsubscribe.html", email=email)

    @app.get("/shop")
    def shop():
        category = request.args.get("category", "").strip()
        query = request.args.get("q", "").strip()
        tag = request.args.get("tag", "").strip()
        products = PRODUCTS
        if category:
            products = [
                product
                for product in products
                if category.casefold() in product["category"].casefold()
                or category.casefold() == product["segment"].casefold()
            ]
        if query:
            needle = query.casefold()
            products = [
                product
                for product in products
                if needle
                in " ".join(
                    [
                        product["name"],
                        product["category"],
                        product["benefit"],
                        " ".join(product["ingredients"]),
                    ]
                ).casefold()
            ]
        if tag:
            products = [
                product
                for product in products
                if tag.casefold() in {item.casefold() for item in product["tags"]}
            ]
        category_meta = {
            "Skin Care": (
                "Natural Skin Care | Aluyè Naturals",
                "Natural skin care made with unrefined shea butter and botanical ingredients. Whipped body butters, face oils and more from Aluyè Naturals.",
            ),
            "African Black Soap": (
                "Natural African Black Soap | Aluyè Naturals",
                "Authentic handcrafted African black soap made from plantain skins, cocoa pods and shea. Traditional cleanser for face and body. Shop Aluyè Naturals.",
            ),
            "Oil": (
                "Natural Oil | Aluyè Naturals",
                "Cold-pressed botanical face and body oils — rosehip, black seed, coconut and more. No additives, pure and natural. Aluyè Naturals.",
            ),
            "Men": (
                "Natural Men | Aluyè Naturals",
                "Natural men's grooming — beard wash, beard oil and beard balm made with African black soap and shea butter. Shop Aluyè Naturals men's range.",
            ),
        }
        shop_title, shop_description = category_meta.get(
            category,
            (
                "Shop Natural Skin, Hair & Body Care | Aluyè Naturals",
                "Shop Aluyè Naturals — natural skin care, hair care, beard products and African black soap. Premium organic formulas made with pure West African botanical ingredients.",
            ),
        )
        seo = page_seo(
            shop_title,
            shop_description,
            "/shop",
        )
        return render_template(
            "collection.html",
            products=products,
            categories=CATEGORIES,
            product_tags=sorted(
                {tag for product in products for tag in product["tags"]}
            ),
            active_category=category,
            active_tag=tag,
            collection_title=category
            or {"New": "New This Season", "Best Seller": "Best Sellers"}.get(
                tag, "Shop all"
            ),
            query=query,
            seo=seo,
        )

    @app.get("/about")
    def about():
        return render_template(
            "about.html",
            seo=page_seo(
                "Our Story | Aluyè Naturals",
                "The story behind Aluyè Naturals — a natural beauty brand rooted in West African botanical heritage, unrefined ingredients and the belief that everyday care should be a ritual.",
                "/about",
            ),
        )

    @app.get("/loyalty")
    def loyalty():
        return render_template(
            "loyalty.html",
            seo=page_seo(
                "Aluyè Ritual Club | Loyalty Programme",
                "Earn points on Aluyè Naturals purchases and redeem them for products and exclusive offers.",
                "/loyalty",
            ),
        )

    @app.route("/contact", methods=["GET", "POST"])
    def contact():
        sent = False
        if request.method == "POST":
            if request.form.get("company", "").strip():
                return redirect(url_for("contact"))
            name = request.form.get("name", "").strip()
            email = request.form.get("email", "").strip()
            subject = request.form.get("topic", "Website enquiry").strip()
            message = request.form.get("message", "").strip()
            if name and email and message:
                save_contact_message(name, email, subject, message)
                sent = True
            else:
                flash("Please complete your name, email and message.", "error")
        return render_template(
            "contact.html",
            sent=sent,
            seo=page_seo(
                "Contact | Aluyè Naturals",
                "Contact Aluyè Naturals — questions about ingredients, products, orders or delivery. We reply within two business days. Get in touch today.",
                "/contact",
            ),
        )

    @app.get("/blog")
    def blog():
        return render_template(
            "blog.html",
            posts=BLOG_POSTS,
            seo=page_seo(
                "The Aluyè Journal | Natural Beauty Guides",
                "The Aluyè Journal — ingredient guides, ritual tips and stories behind our West African botanical skincare. Read, learn and discover your ritual.",
                "/blog",
            ),
        )

    @app.get("/blog/<slug>")
    def blog_post(slug):
        post = next((item for item in BLOG_POSTS if item["slug"] == slug), None)
        if post is None:
            abort(404)
        return render_template(
            "blog_post.html",
            post=post,
            seo=page_seo(
                f"{post['title']} | The Aluyè Journal",
                post["excerpt"],
                f"/blog/{slug}",
            ),
        )

    @app.get("/products/<slug>")
    def product_detail(slug):
        from admin import get_db
        product = get_product(slug)
        record_product_event(slug, "view")
        seo = page_seo(
            f"{product['name']} | Aluyè Naturals",
            f"{product['name']} by Aluyè Naturals. {product.get('benefit') or product.get('description', '')} Natural ingredients, small-batch made. Delivered across Canada.",
            f"/products/{slug}",
            product["image"],
        )
        related = [
            item
            for item in PRODUCTS
            if item["slug"] != slug and item["category"] == product["category"]
        ][:3]
        if len(related) < 3:
            related += [
                item
                for item in PRODUCTS
                if item["slug"] != slug and item not in related
            ][: 3 - len(related)]
        reviews = get_db().execute(
            "SELECT name, rating, title, body, created_at FROM reviews WHERE product_slug=? AND status='approved' ORDER BY created_at DESC",
            (slug,),
        ).fetchall()
        return render_template(
            "product.html",
            product=product,
            related=related,
            reviews=reviews,
            seo=seo,
            structured_data=[
                {
                    "@context": "https://schema.org",
                    "@type": "Product",
                    "name": product["name"],
                    "description": product["description"],
                    "image": [
                        absolute_url(
                            url_for(
                                "media",
                                collection="products",
                                filename=product["image"],
                            )
                        )
                    ],
                    "brand": {"@type": "Brand", "name": "Aluyè Naturals"},
                    "offers": {
                        "@type": "Offer",
                        "priceCurrency": "CAD",
                        "price": product["price"],
                        "availability": "https://schema.org/InStock",
                        "url": absolute_url(f"/products/{slug}"),
                    },
                }
            ],
        )

    @app.post("/cart/add/<slug>")
    def cart_add(slug):
        get_product(slug)
        record_product_event(slug, "cart")
        quantity = parse_quantity(request.form.get("quantity", "1"))
        cart = session.get("cart", {})
        cart[slug] = cart.get(slug, 0) + quantity
        session["cart"] = cart
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            items, subtotal = cart_summary()
            return {
                "ok": True,
                "cart_count": sum(session.get("cart", {}).values()),
                "subtotal": subtotal,
                "items": [
                    {
                        "slug": i["product"]["slug"],
                        "name": i["product"]["name"],
                        "image": i["product"]["image"],
                        "price": i["product"]["price"],
                        "size": i["product"].get("size", ""),
                        "category": i["product"].get("category", ""),
                        "quantity": i["quantity"],
                        "line_total": i["line_total"],
                    }
                    for i in items
                ],
            }
        flash("Added to your bag.", "success")
        next_url = request.form.get("next", "")
        return redirect(next_url if next_url.startswith("/") else url_for("cart"))

    @app.get("/cart")
    def cart():
        items, subtotal = cart_summary()
        seo = page_seo(
            "Your Shopping Bag | Aluyè Naturals",
            "Review the natural care products in your Aluyè Naturals shopping bag.",
            "/cart",
            robots="noindex,follow",
        )
        return render_template(
            "cart.html",
            items=items,
            subtotal=subtotal,
            seo=seo,
        )

    def _cart_json():
        items, subtotal = cart_summary()
        return {
            "ok": True,
            "cart_count": sum(session.get("cart", {}).values()),
            "subtotal": subtotal,
            "items": [
                {
                    "slug": i["product"]["slug"],
                    "name": i["product"]["name"],
                    "image": i["product"]["image"],
                    "price": i["product"]["price"],
                    "size": i["product"].get("size", ""),
                    "category": i["product"].get("category", ""),
                    "quantity": i["quantity"],
                    "line_total": i["line_total"],
                }
                for i in items
            ],
        }

    @app.get("/api/cart")
    def api_cart():
        return _cart_json()

    @app.post("/cart/update/<slug>")
    def cart_update(slug):
        get_product(slug)
        quantity = parse_quantity(request.form.get("quantity", "1"), allow_zero=True)
        cart = session.get("cart", {})
        if quantity == 0:
            cart.pop(slug, None)
        else:
            cart[slug] = quantity
        session["cart"] = cart
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return _cart_json()
        return redirect(url_for("cart"))

    @app.post("/cart/remove/<slug>")
    def cart_remove(slug):
        cart = session.get("cart", {})
        cart.pop(slug, None)
        session["cart"] = cart
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return _cart_json()
        flash("Item removed from your bag.", "success")
        return redirect(url_for("cart"))

    def validate_checkout_form(form):
        errors = {}
        for field in ("email", "first_name", "last_name", "address", "city", "postal_code", "country"):
            if not form.get(field):
                errors[field] = "Please complete this field."
        if form.get("email") and "@" not in form["email"]:
            errors["email"] = "Enter a valid email address."
        return errors

    def quote_shipping(form, method="standard"):
        from admin import calculate_shipping

        return calculate_shipping(form.get("postal_code", ""), form.get("country", ""), method=method)

    def send_order_emails(order_number, form, items, subtotal, shipping_fee, zone_name, payment_method, transaction_id):
        from admin import get_admin_email, send_mail

        settings = load_setting("settings", {}) or {}
        address_line = ", ".join(
            part for part in [form.get("address"), form.get("apartment"), form.get("city"), form.get("postal_code"), form.get("country")] if part
        )
        order_date = datetime.now().strftime("%B %d, %Y at %I:%M %p")
        common_ctx = dict(
            order_number=order_number,
            items=items,
            subtotal=subtotal,
            delivery=shipping_fee,
            total=subtotal + shipping_fee,
            zone_name=zone_name,
            site_url=app.config["SITE_URL"],
            address_line=address_line,
            phone=form.get("phone", ""),
            payment_method=payment_method,
            transaction_id=transaction_id,
            order_date=order_date,
        )
        customer_html = render_template(
            "emails/order_confirmation.html",
            customer_name=form.get("first_name", ""),
            contact_email=settings.get("contact_email", ""),
            **common_ctx,
        )
        send_mail(
            subject=f"Your Aluyè Naturals order is confirmed 🌿 (#{order_number})",
            recipients=[form["email"]],
            html=customer_html,
        )
        admin_html = render_template(
            "emails/admin_order_notification.html",
            customer_name=f"{form.get('first_name','')} {form.get('last_name','')}".strip(),
            customer_email=form.get("email", ""),
            **common_ctx,
        )
        send_mail(
            subject=f"New order {order_number} — CAD ${subtotal + shipping_fee:.2f}",
            recipients=[get_admin_email()],
            html=admin_html,
        )

    def place_order(form, items, subtotal, shipping_quote, payment_method, status="Pending", transaction_id=""):
        order_number = f"AN-{abs(hash((form['email'], subtotal, datetime.now().timestamp()))) % 900000 + 100000}"
        shipping_fee = shipping_quote["rate"] or 0
        save_order(
            order_number, form, items, subtotal,
            shipping_fee=shipping_fee, payment_method=payment_method,
            status=status, transaction_id=transaction_id,
        )
        deduct_stock(items)
        try:
            send_order_emails(
                order_number, form, items, subtotal, shipping_fee,
                shipping_quote.get("zone_name"), payment_method, transaction_id,
            )
        except Exception as exc:
            print(f"Order email error for {order_number}: {exc}")
        session.pop("cart", None)
        return order_number, shipping_fee

    @app.route("/checkout", methods=["GET", "POST"])
    def checkout():

        items, subtotal = cart_summary()
        if not items:
            flash("Your bag is empty.", "error")
            return redirect(url_for("shop"))
        errors = {}
        form = {}
        settings = load_setting("settings", {}) or {}
        paypal_client_id = settings.get("paypal_client") if settings.get("paypal_configured") else None

        shipping_method = request.values.get("shipping_method", "standard")
        preview_form = {"postal_code": request.values.get("postal_code", ""), "country": request.values.get("country", "")}
        shipping_quote = quote_shipping(preview_form, shipping_method) if request.method == "GET" else None

        if request.method == "POST":
            form = {key: request.form.get(key, "").strip() for key in CHECKOUT_FIELDS}
            errors = validate_checkout_form(form)
            shipping_quote = quote_shipping(form, shipping_method)
            if not shipping_quote["available"]:
                if shipping_quote["needs_quote"]:
                    errors["postal_code"] = "We don't have automatic delivery pricing for this address — we'll follow up with a manual shipping quote."
                else:
                    errors["postal_code"] = "Sorry, we don't currently deliver to this address."
            if not errors:
                order_number, shipping_fee = place_order(
                    form, items, subtotal, shipping_quote, payment_method="Bank Transfer / Online Payment"
                )
                return render_template(
                    "confirmation.html",
                    order_number=order_number,
                    customer=form,
                    items=items,
                    subtotal=subtotal,
                    delivery=shipping_fee,
                    total=subtotal + shipping_fee,
                    seo=page_seo(
                        "Order Confirmed | Aluyè Naturals",
                        "Your Aluyè Naturals order is confirmed.",
                        "/checkout",
                        robots="noindex,nofollow",
                    ),
                )
        delivery = shipping_quote["rate"] or 0 if shipping_quote and shipping_quote["available"] else 0
        return render_template(
            "checkout.html",
            items=items,
            subtotal=subtotal,
            delivery=delivery,
            total=subtotal + delivery,
            shipping_quote=shipping_quote,
            paypal_client_id=paypal_client_id,
            is_admin=bool(session.get("admin_user_id")),
            s=settings,
            errors=errors,
            form=form,
            seo=page_seo(
                "Secure Checkout | Aluyè Naturals",
                "Complete your Aluyè Naturals order securely.",
                "/checkout",
                robots="noindex,nofollow",
            ),
        )

    @app.post("/api/shipping-quote")
    def shipping_quote_api():
        postal_code = request.form.get("postal_code", "")
        country = request.form.get("country", "")
        method = request.form.get("shipping_method", "standard")
        quote = quote_shipping({"postal_code": postal_code, "country": country}, method)
        return quote

    @app.post("/api/paypal/create-order")
    def paypal_create_order_route():
        import paypal_client

        settings = load_setting("settings", {}) or {}
        if not paypal_client.is_configured(settings):
            return {"error": "PayPal is not configured."}, 400

        items, subtotal = cart_summary()
        if not items:
            return {"error": "Your bag is empty."}, 400

        form = {key: request.form.get(key, "").strip() for key in CHECKOUT_FIELDS}
        errors = validate_checkout_form(form)
        shipping_method = request.form.get("shipping_method", "standard")
        quote = quote_shipping(form, shipping_method)
        if not quote["available"]:
            return {"error": "We don't currently deliver to this address."}, 400
        if errors:
            return {"error": "Please complete all required fields.", "fields": errors}, 400

        total = subtotal + (quote["rate"] or 0)
        try:
            order = paypal_client.create_order(settings, total, currency="CAD")
        except Exception as exc:
            print(f"PayPal create-order error: {exc}")
            return {"error": "Could not start PayPal checkout. Please try again."}, 502
        return {"id": order["id"]}

    @app.post("/api/paypal/capture-order/<paypal_order_id>")
    def paypal_capture_order_route(paypal_order_id):
        import paypal_client

        settings = load_setting("settings", {}) or {}
        if not paypal_client.is_configured(settings):
            return {"ok": False, "error": "PayPal is not configured."}, 400

        items, subtotal = cart_summary()
        if not items:
            return {"ok": False, "error": "Your bag is empty."}, 400

        form = {key: request.form.get(key, "").strip() for key in CHECKOUT_FIELDS}
        errors = validate_checkout_form(form)
        if errors:
            return {"ok": False, "error": "Please complete all required fields."}, 400

        shipping_method = request.form.get("shipping_method", "standard")
        quote = quote_shipping(form, shipping_method)
        if not quote["available"]:
            return {"ok": False, "error": "We don't currently deliver to this address."}, 400

        try:
            capture = paypal_client.capture_order(settings, paypal_order_id)
        except Exception as exc:
            print(f"PayPal capture error: {exc}")
            return {"ok": False, "error": "PayPal payment could not be captured."}, 502

        if capture.get("status") != "COMPLETED":
            return {"ok": False, "error": "PayPal payment was not completed."}, 400

        transaction_id = paypal_client.extract_capture_id(capture)
        order_number, shipping_fee = place_order(
            form, items, subtotal, quote,
            payment_method="PayPal", status="Paid", transaction_id=transaction_id,
        )
        return {"ok": True, "redirect": url_for("checkout_confirmation", order_number=order_number)}

    @app.get("/checkout/confirmation/<order_number>")
    def checkout_confirmation(order_number):
        from admin import get_db

        order = get_db().execute(
            "SELECT * FROM orders WHERE order_number=?", (order_number,)
        ).fetchone()
        if not order:
            abort(404)
        return render_template(
            "confirmation.html",
            order_number=order["order_number"],
            customer={"first_name": order["customer_name"].split(" ")[0], "email": order["email"]},
            items=json.loads(order["items"]),
            subtotal=order["total"] - order["shipping_fee"],
            delivery=order["shipping_fee"],
            total=order["total"],
            seo=page_seo(
                "Order Confirmed | Aluyè Naturals",
                "Your Aluyè Naturals order is confirmed.",
                "/checkout",
                robots="noindex,nofollow",
            ),
        )

    @app.get("/checkout/payment-failed")
    def checkout_payment_failed():
        return render_template(
            "payment_status.html",
            status="failed",
            seo=page_seo("Payment Failed | Aluyè Naturals", "Your payment could not be completed.", "/checkout/payment-failed", robots="noindex,nofollow"),
        )

    @app.get("/checkout/payment-cancelled")
    def checkout_payment_cancelled():
        return render_template(
            "payment_status.html",
            status="cancelled",
            seo=page_seo("Payment Cancelled | Aluyè Naturals", "Your payment was cancelled.", "/checkout/payment-cancelled", robots="noindex,nofollow"),
        )

    @app.post("/products/<slug>/review")
    def submit_review(slug):
        from admin import get_db, add_notification
        get_product(slug)
        name = request.form.get("reviewer_name", "").strip()
        email = request.form.get("reviewer_email", "").strip()
        rating = request.form.get("rating", "5")
        title = request.form.get("review_title", "").strip()
        body_text = request.form.get("review_body", "").strip()
        if name and email and title and body_text:
            try:
                rating = min(5, max(1, int(rating)))
            except (ValueError, TypeError):
                rating = 5
            db = get_db()
            db.execute(
                "INSERT INTO reviews(product_slug, name, email, rating, title, body, created_at) VALUES(?,?,?,?,?,?,?)",
                (slug, name, email, rating, title, body_text,
                 __import__("datetime").datetime.now().isoformat(timespec="minutes")),
            )
            db.commit()
            add_notification("review", "New review submitted", f"{name} reviewed {slug}")
            flash("Thank you! Your review is pending approval.", "success")
        else:
            flash("Please complete all fields.", "error")
        return redirect(url_for("product_detail", slug=slug))

    @app.route("/track-order", methods=["GET", "POST"])
    def track_order():
        from admin import get_db
        order = None
        error = None
        if request.method == "POST":
            order_number = request.form.get("order_number", "").strip()
            email = request.form.get("email", "").strip()
            if order_number and email:
                order = get_db().execute(
                    "SELECT * FROM orders WHERE order_number=? AND email=?",
                    (order_number, email),
                ).fetchone()
                if not order:
                    error = "Order not found. Please check your order number and email."
            else:
                error = "Please enter both your order number and email."
        return render_template(
            "track_order.html",
            order=order,
            error=error,
            seo=page_seo("Track Your Order | Aluyè Naturals", "Track the status of your Aluyè Naturals order.", "/track-order", robots="noindex,follow"),
        )

    @app.route("/returns", methods=["GET", "POST"])
    def returns():
        from admin import get_db, add_notification
        submitted = False
        reference = None
        if request.method == "POST":
            order_number = request.form.get("order_number", "").strip()
            email = request.form.get("email", "").strip()
            items_text = request.form.get("items", "").strip()
            reason = request.form.get("reason", "").strip()
            details = request.form.get("details", "").strip()
            refund_method = request.form.get("refund_method", "").strip()
            if order_number and email and items_text and reason and refund_method:
                reference = f"RET-{abs(hash((order_number, email))) % 900000 + 100000}"
                db = get_db()
                db.execute(
                    "INSERT OR IGNORE INTO return_requests(reference, order_number, email, items, reason, details, refund_method, created_at) VALUES(?,?,?,?,?,?,?,?)",
                    (reference, order_number, email, items_text, reason, details, refund_method,
                     __import__("datetime").datetime.now().isoformat(timespec="minutes")),
                )
                db.commit()
                add_notification("return", "New return request", f"{reference} for {order_number}")
                submitted = True
            else:
                flash("Please complete all required fields.", "error")
        return render_template(
            "returns.html",
            submitted=submitted,
            reference=reference,
            seo=page_seo("Returns & Refunds | Aluyè Naturals", "Request a return or refund for your Aluyè Naturals order.", "/returns"),
        )

    @app.get("/wishlist")
    def wishlist_page():
        return render_template(
            "wishlist.html",
            products=PRODUCTS,
            seo=page_seo("Your Wishlist | Aluyè Naturals", "View your saved Aluyè Naturals products.", "/wishlist", robots="noindex,follow"),
        )

    @app.get("/compare")
    def compare_page():
        return render_template(
            "compare.html",
            products=PRODUCTS,
            seo=page_seo("Compare Products | Aluyè Naturals", "Compare Aluyè Naturals products side by side.", "/compare", robots="noindex,follow"),
        )

    @app.route("/login", methods=["GET", "POST"])
    def login():
        from admin import get_db
        from werkzeug.security import check_password_hash
        if request.method == "POST":
            email = request.form.get("email", "").strip()
            password = request.form.get("password", "")
            db = get_db()
            user = db.execute("SELECT * FROM customers WHERE email=?", (email,)).fetchone()
            if user and check_password_hash(user["password_hash"], password):
                session["customer_id"] = user["id"]
                session["customer_name"] = user["first_name"]
                session["customer_email"] = user["email"]
                flash(f"Welcome back, {user['first_name']}!", "success")
                next_url = request.args.get("next", url_for("account"))
                return redirect(next_url)
            flash("Incorrect email or password.", "error")
        return render_template("auth/login.html")

    @app.route("/register", methods=["GET", "POST"])
    def register():
        from admin import get_db, add_notification
        from werkzeug.security import generate_password_hash
        if request.method == "POST":
            first = request.form.get("first_name", "").strip()
            last = request.form.get("last_name", "").strip()
            email = request.form.get("email", "").strip()
            pw = request.form.get("password", "")
            pw2 = request.form.get("confirm_password", "")
            if not all([first, last, email, pw]):
                flash("Please complete all fields.", "error")
            elif pw != pw2:
                flash("Passwords do not match.", "error")
            elif len(pw) < 8:
                flash("Password must be at least 8 characters.", "error")
            else:
                db = get_db()
                if db.execute("SELECT 1 FROM customers WHERE email=?", (email,)).fetchone():
                    flash("An account with this email already exists.", "error")
                else:
                    db.execute(
                        "INSERT INTO customers(first_name,last_name,email,password_hash,created_at) VALUES(?,?,?,?,?)",
                        (first, last, email, generate_password_hash(pw),
                         __import__("datetime").datetime.now().isoformat(timespec="minutes")),
                    )
                    db.commit()
                    session["customer_id"] = db.execute("SELECT id FROM customers WHERE email=?", (email,)).fetchone()["id"]
                    session["customer_name"] = first
                    session["customer_email"] = email
                    add_notification("customer", "New customer", f"{first} {last} ({email})")
                    flash(f"Welcome to Aluyè, {first}! Check your email for your 15% off code.", "success")
                    return redirect(url_for("account"))
        return render_template("auth/register.html")

    @app.get("/logout")
    def logout():
        session.pop("customer_id", None)
        session.pop("customer_name", None)
        session.pop("customer_email", None)
        flash("Signed out.", "success")
        return redirect(url_for("home"))

    @app.get("/account")
    def account():
        if not session.get("customer_id"):
            return redirect(url_for("login", next=request.path))
        from admin import get_db
        orders = get_db().execute(
            "SELECT * FROM orders WHERE email=? ORDER BY created_at DESC",
            (session.get("customer_email", ""),)
        ).fetchall()
        return render_template("auth/account.html", orders=orders, products=PRODUCTS,
            seo=page_seo("My Account | Aluyè Naturals", "Manage your Aluyè Naturals account.", "/account", robots="noindex"))

    @app.get("/privacy-policy")
    def privacy_policy():
        return render_template("legal/privacy.html",
            seo=page_seo("Privacy Policy | Aluyè Naturals", "How Aluyè Naturals handles your data.", "/privacy-policy"))

    @app.get("/terms-of-service")
    def terms():
        return render_template("legal/terms.html",
            seo=page_seo("Terms of Service | Aluyè Naturals", "Terms and conditions for Aluyè Naturals.", "/terms-of-service"))

    @app.get("/gift-cards")
    def gift_cards():
        return render_template("gift_cards.html", products=PRODUCTS,
            seo=page_seo("Gift Cards | Aluyè Naturals", "Give the gift of natural care.", "/gift-cards"))

    @app.get("/quiz")
    def quiz():
        return render_template(
            "quiz.html",
            products=PRODUCTS,
            seo=page_seo("Find Your Ritual | Aluyè Naturals", "Take our quiz to discover your perfect Aluyè Naturals routine.", "/quiz"),
        )

    @app.get("/ingredients")
    def ingredients_page():
        return render_template(
            "ingredients_page.html",
            ingredients=INGREDIENTS,
            products=PRODUCTS,
            seo=page_seo("Ingredients | Aluyè Naturals", "Explore the natural ingredients behind Aluyè Naturals.", "/ingredients"),
        )

    @app.get("/offline")
    def offline():
        return render_template("offline.html")

    @app.get("/sw.js")
    def service_worker():
        return send_from_directory(BASE_DIR / "static", "sw.js", mimetype="application/javascript")

    @app.get("/manifest.json")
    def manifest():
        return send_from_directory(BASE_DIR / "static", "manifest.json", mimetype="application/manifest+json")

    @app.get("/robots.txt")
    def robots():
        content = (
            "User-agent: *\n"
            "Allow: /\n\n"
            f"Sitemap: {absolute_url('/sitemap.xml')}\n"
        )
        response = make_response(content)
        response.headers["Content-Type"] = "text/plain; charset=utf-8"
        return response

    @app.get("/sitemap.xml")
    def sitemap():
        pages = [
            {"loc": absolute_url("/"), "changefreq": "weekly", "priority": "1.0"},
            {"loc": absolute_url("/shop"), "changefreq": "weekly", "priority": "0.9"},
            {"loc": absolute_url("/about"), "changefreq": "monthly", "priority": "0.7"},
            {"loc": absolute_url("/loyalty"), "changefreq": "monthly", "priority": "0.6"},
            {"loc": absolute_url("/contact"), "changefreq": "monthly", "priority": "0.5"},
            {"loc": absolute_url("/blog"), "changefreq": "weekly", "priority": "0.7"},
            *[
                {
                    "loc": absolute_url(f"/products/{product['slug']}"),
                    "changefreq": "weekly",
                    "priority": "0.8",
                }
                for product in PRODUCTS
            ],
            *[
                {
                    "loc": absolute_url(f"/blog/{post['slug']}"),
                    "changefreq": "monthly",
                    "priority": "0.6",
                }
                for post in BLOG_POSTS
            ],
        ]
        response = make_response(render_template("sitemap.xml", pages=pages))
        response.headers["Content-Type"] = "application/xml; charset=utf-8"
        return response

    @app.after_request
    def add_response_headers(response):
        if request.endpoint == "static":
            response.headers.setdefault("Cache-Control", "public, max-age=31536000, immutable")
        elif request.endpoint == "media":
            response.headers.setdefault("Cache-Control", "public, max-age=604800")
        if (
            "gzip" in request.headers.get("Accept-Encoding", "").lower()
            and not response.direct_passthrough
            and response.status_code == 200
            and response.content_length
            and response.content_length > 500
            and response.mimetype
            and (
                response.mimetype.startswith("text/")
                or response.mimetype
                in {
                    "application/javascript",
                    "application/json",
                    "application/ld+json",
                    "application/xml",
                }
            )
            and "Content-Encoding" not in response.headers
        ):
            compressed = gzip.compress(response.get_data(), compresslevel=6)
            response.set_data(compressed)
            response.headers["Content-Encoding"] = "gzip"
            response.headers["Content-Length"] = len(compressed)
            response.headers["Vary"] = "Accept-Encoding"
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        return response

    def absolute_url(path):
        if path.startswith(("http://", "https://")):
            return path
        return f"{app.config['SITE_URL']}/{path.lstrip('/')}"

    def page_seo(title, description, path, image=None, robots=None):
        title = clean_meta(title, DEFAULT_META_TITLE)
        description = clean_meta(description, DEFAULT_META_DESCRIPTION)
        image_url = (
            absolute_url(url_for("media", collection="products", filename=image))
            if image
            else absolute_url(
                url_for("media", collection="hero", filename="aluye-chlorophyll-hero.webp")
            )
        )
        return {
            "title": title,
            "description": description,
            "canonical_url": absolute_url(path),
            "image_url": image_url,
            "image_alt": title.split("|", 1)[0].strip(),
            "robots": robots
            or "index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1",
        }

    def get_product(slug):
        product = next((item for item in PRODUCTS if item["slug"] == slug), None)
        if product is None:
            abort(404)
        return product

    def parse_quantity(value, allow_zero=False):
        try:
            quantity = int(value)
        except (TypeError, ValueError):
            quantity = 1
        minimum = 0 if allow_zero else 1
        return min(10, max(minimum, quantity))

    def cart_summary():
        items = []
        subtotal = 0
        for slug, quantity in session.get("cart", {}).items():
            product = next((item for item in PRODUCTS if item["slug"] == slug), None)
            if not product:
                continue
            line_total = product["price"] * quantity
            subtotal += line_total
            items.append(
                {"product": product, "quantity": quantity, "line_total": line_total}
            )
        return items, subtotal

    def build_breadcrumbs():
        endpoint = request.endpoint
        if not endpoint or endpoint in {"home", "static", "media", "health"}:
            return []

        crumbs = [{"label": "Home", "url": url_for("home")}]
        labels = {
            "about": "About",
            "contact": "Contact",
            "blog": "Journal",
            "cart": "Shopping bag",
            "checkout": "Checkout",
            "loyalty": "Ritual Club",
        }

        if endpoint == "shop":
            category = request.args.get("category", "").strip()
            tag = request.args.get("tag", "").strip()
            crumbs.append(
                {
                    "label": "Shop",
                    "url": url_for("shop") if category or tag else None,
                }
            )
            if category:
                crumbs.append({"label": category, "url": None})
            elif tag:
                crumbs.append({"label": tag, "url": None})
        elif endpoint == "product_detail":
            product = next(
                (
                    item
                    for item in PRODUCTS
                    if item["slug"] == request.view_args.get("slug")
                ),
                None,
            )
            crumbs.append({"label": "Shop", "url": url_for("shop")})
            if product:
                crumbs.append(
                    {
                        "label": product["segment"],
                        "url": url_for("shop", category=product["segment"]),
                    }
                )
                crumbs.append({"label": product["name"], "url": None})
        elif endpoint == "blog_post":
            post = next(
                (
                    item
                    for item in BLOG_POSTS
                    if item["slug"] == request.view_args.get("slug")
                ),
                None,
            )
            crumbs.append({"label": "Journal", "url": url_for("blog")})
            crumbs.append(
                {"label": post["title"] if post else "Article", "url": None}
            )
        else:
            crumbs.append(
                {
                    "label": labels.get(
                        endpoint, endpoint.replace("_", " ").title()
                    ),
                    "url": None,
                }
            )
        return crumbs

    @app.errorhandler(404)
    def not_found(e):
        return render_template("404.html", seo={"title": "Page Not Found | Aluyè Naturals", "description": "", "canonical_url": "", "image_url": "", "image_alt": "", "robots": "noindex"}), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template("500.html", seo={"title": "Something Went Wrong | Aluyè Naturals", "description": "", "canonical_url": "", "image_url": "", "image_alt": "", "robots": "noindex"}), 500

    return app


PRODUCTS = [
    {
        "slug": "chlorophyll-whipped-shea-butter",
        "name": "Chlorophyll Whipped Shea Butter",
        "category": "Body",
        "benefit": "Deep moisture with a fresh mango-papaya finish.",
        "price": 25,
        "size": "120g",
        "rating": 4.9,
        "reviews": 42,
        "badge": "Best Seller",
        "image": "photo_2_2026-06-08_18-19-49.webp",
        "description": "An airy, fast-melting body butter made with unrefined shea, nourishing oils and a fresh mango-papaya botanical blend.",
        "ingredients": ["Unrefined shea butter", "Grapeseed oil", "Coconut oil", "Olive oil", "Chlorophyll"],
        "best_for": "Dry or dull-looking skin seeking rich moisture without a waxy finish.",
        "how_to": "Warm a small amount between your palms and massage into slightly damp skin.",
    },
    {
        "slug": "lemongrass-whipped-shea-butter",
        "name": "Lemongrass Whipped Shea Butter",
        "category": "Body",
        "benefit": "A bright, energising ritual for soft, supple skin.",
        "price": 25,
        "size": "120g",
        "rating": 4.8,
        "reviews": 31,
        "badge": "Fresh",
        "image": "photo_3_2026-06-05_22-40-06.webp",
        "description": "A whipped shea moisturiser with a bright lemongrass aroma and a silky, cushiony finish.",
        "ingredients": ["Unrefined shea butter", "Grapeseed oil", "Coconut oil", "Olive oil", "Lemongrass extract"],
        "best_for": "Daily body moisture and an uplifting morning or post-shower ritual.",
        "how_to": "Smooth over clean skin, concentrating on elbows, knees and other dry areas.",
    },
    {
        "slug": "activated-charcoal-cleanser",
        "name": "Activated Charcoal Cleanser",
        "category": "Face · Hair · Body",
        "benefit": "A purifying three-in-one cleanse that respects moisture.",
        "price": 25,
        "size": "16oz",
        "rating": 4.9,
        "reviews": 56,
        "badge": "Multi-use",
        "image": "photo_1_2026-06-08_18-19-49.webp",
        "description": "A multi-use black soap cleanser with activated bamboo charcoal and mineral-rich Himalayan pink salt.",
        "ingredients": ["African black soap", "Spring water", "Activated bamboo charcoal", "Himalayan pink salt"],
        "best_for": "A thorough face, body or scalp cleanse, especially where excess oil builds up.",
        "how_to": "Work a small amount into wet hands, massage gently, then rinse thoroughly.",
    },
    {
        "slug": "shea-grow-hair-scalp-oil",
        "name": "Shea-Grow Hair & Scalp Oil",
        "category": "Hair & Scalp",
        "benefit": "A concentrated botanical oil for nourished roots and shine.",
        "price": 23,
        "size": "50ml",
        "rating": 4.7,
        "reviews": 28,
        "badge": "Ritual Pick",
        "image": "photo_4_2026-06-05_22-40-06.webp",
        "description": "A concentrated blend of botanical oils designed to keep the scalp comfortable and hair looking nourished and glossy.",
        "ingredients": ["Castor oil", "Black seed oil", "Avocado oil", "Coconut oil", "Rosemary", "Tea tree oil"],
        "best_for": "Dry scalp, protective styles and hair that needs extra softness and shine.",
        "how_to": "Apply sparingly to the scalp or lengths and massage in. Use as a treatment or finishing oil.",
    },
]

CATEGORIES = ["Body", "Face", "Hair & Scalp", "Beard & Grooming", "Raw Essentials"]
CHECKOUT_FIELDS = (
    "email",
    "first_name",
    "last_name",
    "address",
    "apartment",
    "city",
    "postal_code",
    "country",
    "phone",
)

RITUALS = [
    {"name": "Body", "detail": "Butters, oils & scrubs", "image": "photo_10_2026-06-08_18-19-49.webp"},
    {"name": "Face", "detail": "Cleanse, balance & glow", "image": "photo_1_2026-06-08_18-19-49.webp"},
    {"name": "Hair & Scalp", "detail": "Nourish from root to tip", "image": "photo_4_2026-06-05_22-40-06.webp"},
    {"name": "Beard", "detail": "Cleanse, soften & style", "image": "photo_6_2026-06-08_18-19-49.webp"},
    {"name": "Raw Essentials", "detail": "Pure, versatile ingredients", "image": "photo_2026-06-09_11-04-04.webp"},
]

INGREDIENTS = [
    {"name": "Unrefined Shea", "origin": "West Africa", "copy": "Rich in naturally occurring fatty acids for lasting softness."},
    {"name": "African Black Soap", "origin": "Traditional craft", "copy": "A plant-based cleanser made for a thorough, balanced wash."},
    {"name": "Activated Charcoal", "origin": "Bamboo-derived", "copy": "Helps lift surface impurities and excess oil from skin."},
    {"name": "Black Seed Oil", "origin": "Cold-pressed", "copy": "A treasured botanical oil for skin, scalp, and hair rituals."},
]

TESTIMONIALS = [
    {"quote": "The texture melts in beautifully and my skin stays comfortable all day.", "name": "Amara", "product": "Whipped Shea Butter"},
    {"quote": "The cleanser feels thorough without leaving my face tight or stripped.", "name": "Nia", "product": "Charcoal Cleanser"},
    {"quote": "A simple ritual that makes my beard feel softer and much easier to style.", "name": "Malik", "product": "Beard Balm"},
]

JOURNAL = [
    {"tag": "Ingredient Guide", "title": "Why unrefined shea feels different", "copy": "From texture to sourcing, discover what makes raw shea a ritual essential."},
    {"tag": "Ritual", "title": "Layering oils and butters for lasting moisture", "copy": "A straightforward guide to sealing in hydration without a heavy finish."},
    {"tag": "Our Story", "title": "Beauty wisdom, carried forward", "copy": "How heritage ingredients inspire a modern approach to everyday care."},
]

PRODUCTS = CATALOG_PRODUCTS
best_seller_slugs = {
    "chlorophyll-whipped-shea-butter",
    "activated-charcoal-cleanser",
    "shea-grow-hair-scalp-oil",
}
for index, product in enumerate(PRODUCTS):
    product.setdefault("rating", round(4.6 + (index % 4) * 0.1, 1))
    product.setdefault("reviews", 18 + index * 3)
    product["is_new"] = index >= len(PRODUCTS) - 3
    tags = {product["badge"]}
    if product["slug"] in best_seller_slugs:
        tags.add("Best Seller")
    if product["is_new"]:
        tags.add("New")
    product["tags"] = sorted(tags)
CATEGORIES = CATALOG_CATEGORIES
HERO_SLIDES = CATALOG_HERO_SLIDES
INGREDIENTS = CATALOG_INGREDIENTS
JOURNAL = CATALOG_BLOG_POSTS
BLOG_POSTS = CATALOG_BLOG_POSTS


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
