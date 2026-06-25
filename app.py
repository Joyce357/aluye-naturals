import gzip
import os
from pathlib import Path

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
    init_admin,
    load_setting,
    record_page_view,
    record_product_event,
    save_contact_message,
    save_order,
)


BASE_DIR = Path(__file__).resolve().parent
FREE_SHIPPING_THRESHOLD = 50


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-change-me"),
        SITE_URL=os.environ.get("SITE_URL", "http://127.0.0.1:5000").rstrip("/"),
    )
    if test_config:
        app.config.update(test_config)
    init_admin(app, PRODUCTS, CATEGORIES, BLOG_POSTS)

    @app.before_request
    def track_storefront_visit():
        if request.method == "GET" and not request.path.startswith(
            ("/admin", "/static", "/media", "/health")
        ):
            settings = load_setting("settings", {}) or {}
            if settings.get("store_status", "").lower() == "maintenance":
                return render_template(
                    "maintenance.html",
                    message=settings.get("maintenance_message")
                    or "We are preparing something beautiful. Please check back shortly.",
                ), 503
            record_page_view(request.path)

    @app.context_processor
    def inject_site_metadata():
        _, cart_subtotal = cart_summary()
        shipping_remaining = max(0, FREE_SHIPPING_THRESHOLD - cart_subtotal)
        site_settings = load_setting("settings", {}) or {}
        homepage_settings = load_setting("homepage", {}) or {}
        return {
            "site_name": site_settings.get("store_name") or "Aluyè Naturals",
            "site_url": app.config["SITE_URL"],
            "cart_count": sum(session.get("cart", {}).values()),
            "cart_subtotal": cart_subtotal,
            "shipping_remaining": shipping_remaining,
            "shipping_progress": min(
                100, round(cart_subtotal / FREE_SHIPPING_THRESHOLD * 100)
            ),
            "free_shipping_threshold": FREE_SHIPPING_THRESHOLD,
            "breadcrumbs": build_breadcrumbs(),
            "site_settings": site_settings,
            "homepage_settings": homepage_settings,
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
            "title": "Natural Shea Butter Skin, Hair & Body Care | Aluyè Naturals",
            "description": (
                "Discover small-batch skin, hair, body and beard care made with "
                "unrefined West African shea butter and thoughtfully sourced botanicals."
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
        seo = page_seo(
            "Shop Natural Skin, Hair & Body Care | Aluyè Naturals",
            "Shop natural body butter, cleansers, oils and grooming care made with unrefined shea and botanical ingredients.",
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
                "Discover the West African ingredients, beauty traditions and thoughtful sourcing behind Aluyè Naturals.",
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
                "Contact Aluyè Naturals | Scarborough, Ontario",
                "Contact Aluyè Naturals at 22-141 Galloway Road, Scarborough, Ontario M1E 4X4.",
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
                "Read practical ingredient guides, rituals and stories from Aluyè Naturals.",
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
        product = get_product(slug)
        record_product_event(slug, "view")
        seo = page_seo(
            f"{product['name']} | Aluyè Naturals",
            product["benefit"],
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
        return render_template(
            "product.html",
            product=product,
            related=related,
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
                        "priceCurrency": "USD",
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
            delivery_remaining=max(0, FREE_SHIPPING_THRESHOLD - subtotal),
            seo=seo,
        )

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
        return redirect(url_for("cart"))

    @app.post("/cart/remove/<slug>")
    def cart_remove(slug):
        cart = session.get("cart", {})
        cart.pop(slug, None)
        session["cart"] = cart
        flash("Item removed from your bag.", "success")
        return redirect(url_for("cart"))

    @app.route("/checkout", methods=["GET", "POST"])
    def checkout():
        items, subtotal = cart_summary()
        if not items:
            flash("Your bag is empty.", "error")
            return redirect(url_for("shop"))
        errors = {}
        form = {}
        if request.method == "POST":
            form = {key: request.form.get(key, "").strip() for key in CHECKOUT_FIELDS}
            for field in ("email", "first_name", "last_name", "address", "city", "postal_code", "country"):
                if not form[field]:
                    errors[field] = "Please complete this field."
            if form["email"] and "@" not in form["email"]:
                errors["email"] = "Enter a valid email address."
            if not errors:
                delivery = 0 if subtotal >= FREE_SHIPPING_THRESHOLD else 8
                order_number = f"AN-{abs(hash((form['email'], subtotal))) % 900000 + 100000}"
                save_order(order_number, form, items, subtotal + delivery)
                session.pop("cart", None)
                return render_template(
                    "confirmation.html",
                    order_number=order_number,
                    customer=form,
                    items=items,
                    subtotal=subtotal,
                    delivery=delivery,
                    total=subtotal + delivery,
                    seo=page_seo(
                        "Order Confirmed | Aluyè Naturals",
                        "Your Aluyè Naturals order is confirmed.",
                        "/checkout",
                        robots="noindex,nofollow",
                    ),
                )
        delivery = 0 if subtotal >= FREE_SHIPPING_THRESHOLD else 8
        return render_template(
            "checkout.html",
            items=items,
            subtotal=subtotal,
            delivery=delivery,
            total=subtotal + delivery,
            errors=errors,
            form=form,
            seo=page_seo(
                "Secure Checkout | Aluyè Naturals",
                "Complete your Aluyè Naturals order securely.",
                "/checkout",
                robots="noindex,nofollow",
            ),
        )

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
