import json
import os
import sqlite3
import tempfile

from app import create_app


def test_homepage_renders():
    app = create_app({"TESTING": True})
    response = app.test_client().get("/")

    assert response.status_code == 200
    assert b"Shea care" in response.data
    assert b"Shop Aluy" in response.data


def test_health_endpoint():
    app = create_app({"TESTING": True})
    response = app.test_client().get("/health")

    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


def test_homepage_has_seo_metadata_and_valid_json_ld():
    app = create_app({"TESTING": True, "SITE_URL": "https://www.aluyenaturals.example"})
    response = app.test_client().get("/")
    html = response.get_data(as_text=True)

    assert '<link rel="canonical" href="https://www.aluyenaturals.example/">' in html
    assert 'property="og:title"' in html
    assert 'name="twitter:card" content="summary_large_image"' in html

    marker = '<script type="application/ld+json">'
    schemas = [
        json.loads(chunk.split("</script>", 1)[0])
        for chunk in html.split(marker)[1:]
    ]
    assert {schema["@type"] for schema in schemas} == {"OnlineStore", "WebSite"}


def test_robots_and_sitemap_use_configured_site_url():
    app = create_app({"TESTING": True, "SITE_URL": "https://www.aluyenaturals.example"})
    client = app.test_client()

    robots = client.get("/robots.txt")
    sitemap = client.get("/sitemap.xml")

    assert robots.status_code == 200
    assert "Sitemap: https://www.aluyenaturals.example/sitemap.xml" in robots.get_data(as_text=True)
    assert sitemap.status_code == 200
    assert "<loc>https://www.aluyenaturals.example/</loc>" in sitemap.get_data(as_text=True)
    assert "/products/chlorophyll-whipped-shea-butter</loc>" in sitemap.get_data(as_text=True)


def test_shop_and_product_pages_render():
    app = create_app({"TESTING": True})
    client = app.test_client()

    shop = client.get("/shop?category=Skin+Care")
    product = client.get("/products/chlorophyll-whipped-shea-butter")

    assert shop.status_code == 200
    assert b"Chlorophyll Whipped Shea Butter" in shop.data
    assert product.status_code == 200
    assert b"Product" in product.data
    assert b"Add to cart" in product.data


def test_cart_and_checkout_flow():
    app = create_app({"TESTING": True, "SECRET_KEY": "test"})
    client = app.test_client()

    added = client.post(
        "/cart/add/chlorophyll-whipped-shea-butter",
        data={"quantity": "2", "next": "/cart"},
        follow_redirects=True,
    )
    assert added.status_code == 200
    assert b"$50" in added.data

    checkout = client.get("/checkout")
    assert checkout.status_code == 200
    assert b"Complete your order" in checkout.data

    confirmed = client.post(
        "/checkout",
        data={
            "email": "customer@example.com",
            "first_name": "Ada",
            "last_name": "Stone",
            "address": "1 Shea Lane",
            "apartment": "",
            "city": "Lagos",
            "postal_code": "100001",
            "country": "Nigeria",
        },
    )
    assert confirmed.status_code == 200
    assert b"Order confirmed" in confirmed.data


def test_content_pages_and_catalogue_segments_render():
    app = create_app({"TESTING": True})
    client = app.test_client()

    for path in ("/about", "/contact", "/blog", "/blog/why-unrefined-shea-feels-different"):
        response = client.get(path)
        assert response.status_code == 200

    men = client.get("/shop?category=Men")
    black_soap = client.get("/shop?category=African+Black+Soap")
    assert b"Gentlemen" in men.data
    assert b"Organic African Black Soap" in black_soap.data


def test_premium_commerce_features_render_and_shipping_threshold():
    app = create_app({"TESTING": True, "SECRET_KEY": "test"})
    client = app.test_client()

    home = client.get("/").get_data(as_text=True)
    assert "New This Season" in home
    assert "Best Sellers" in home
    assert "Join the Aluyè Ritual Club" in home
    assert 'announcement-ticker-track' in home
    assert home.count('announcement-ticker-group') == 2
    assert "data-quick-view" in home
    assert 'data-currency-selector' in home

    collection = client.get("/shop?category=Skin+Care").get_data(as_text=True)
    assert 'data-sort-products' in collection
    assert 'data-price-filter' in collection
    assert 'data-tag-filter' in collection
    assert 'aria-label="Breadcrumb"' in collection

    client.post(
        "/cart/add/deep-moisturising-rosehip-oil",
        data={"quantity": "1", "next": "/cart"},
    )
    cart = client.get("/cart").get_data(as_text=True)
    assert 'Shopping bag with 1 items' in cart
    assert 'data-price="32"' in cart
    assert "calculated at checkout" in cart

    loyalty = client.get("/loyalty")
    assert loyalty.status_code == 200
    assert b"Ritual Club" in loyalty.data


def test_admin_login_protection_and_sections():
    database = os.path.join(tempfile.mkdtemp(), "admin.db")
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "admin-test",
            "ADMIN_DATABASE": database,
        }
    )
    client = app.test_client()

    protected = client.get("/admin/")
    assert protected.status_code == 302
    assert "/admin/login" in protected.location

    login = client.post(
        "/admin/login",
        data={"username": "admin", "password": "aluye2026"},
        follow_redirects=True,
    )
    assert login.status_code == 200
    assert b"Dashboard" in login.data

    for path in (
        "/admin/products",
        "/admin/orders",
        "/admin/messages",
        "/admin/notifications",
        "/admin/homepage",
        "/admin/global-settings",
        "/admin/section/payments",
        "/admin/shipping",
        "/admin/discounts",
        "/admin/journal",
        "/admin/analytics",
        "/admin/account",
    ):
        assert client.get(path).status_code == 200


def test_contact_message_and_checkout_sync_to_admin():
    database = os.path.join(tempfile.mkdtemp(), "admin.db")
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "admin-sync-test",
            "ADMIN_DATABASE": database,
        }
    )
    client = app.test_client()
    client.post(
        "/contact",
        data={
            "name": "Admin Test",
            "email": "admin-test@example.com",
            "topic": "Product question",
            "message": "Please tell me more.",
        },
    )
    client.post(
        "/cart/add/chlorophyll-whipped-shea-butter",
        data={"quantity": "2", "next": "/cart"},
    )
    client.post(
        "/checkout",
        data={
            "email": "order@example.com",
            "first_name": "Ada",
            "last_name": "Admin",
            "address": "1 Shea Lane",
            "apartment": "",
            "city": "Lagos",
            "postal_code": "100001",
            "country": "Nigeria",
        },
    )
    client.post(
        "/admin/login",
        data={"username": "admin", "password": "aluye2026"},
    )
    assert b"Admin Test" in client.get("/admin/messages").data
    assert b"Ada Admin" in client.get("/admin/orders").data


def test_database_products_survive_app_restart_and_control_storefront():
    database = os.path.join(tempfile.mkdtemp(), "admin.db")
    config = {
        "TESTING": True,
        "SECRET_KEY": "persistence-test",
        "ADMIN_DATABASE": database,
    }
    create_app(config)

    connection = sqlite3.connect(database)
    row = connection.execute(
        "SELECT data FROM products WHERE slug='chlorophyll-whipped-shea-butter'"
    ).fetchone()
    product = json.loads(row[0])
    product["name"] = "Persistent Chlorophyll Shea"
    connection.execute(
        "UPDATE products SET data=? WHERE slug='chlorophyll-whipped-shea-butter'",
        (json.dumps(product),),
    )
    connection.execute(
        "UPDATE products SET status='draft' WHERE slug='activated-charcoal-cleanser'"
    )
    connection.commit()
    connection.close()

    restarted_app = create_app(config)
    client = restarted_app.test_client()
    shop = client.get("/shop").get_data(as_text=True)
    assert "Persistent Chlorophyll Shea" in shop
    assert "Activated Charcoal Cleanser" not in shop


def test_editor_cannot_access_super_admin_sections():
    database = os.path.join(tempfile.mkdtemp(), "admin.db")
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "role-test",
            "ADMIN_DATABASE": database,
        }
    )
    connection = sqlite3.connect(database)
    admin_hash = connection.execute(
        "SELECT password_hash FROM admin_users WHERE username='admin'"
    ).fetchone()[0]
    connection.execute(
        "INSERT INTO admin_users(username,name,email,password_hash,role) VALUES(?,?,?,?,?)",
        ("editor", "Editorial User", "editor@example.com", admin_hash, "Editor"),
    )
    connection.commit()
    connection.close()

    client = app.test_client()
    client.post(
        "/admin/login",
        data={"username": "editor", "password": "aluye2026"},
    )
    assert client.get("/admin/products").status_code == 200
    assert client.get("/admin/journal").status_code == 200
    restricted = client.get("/admin/section/payments", follow_redirects=True)
    assert b"does not have permission" in restricted.data


def test_homepage_editor_reorders_and_hides_categories():
    database = os.path.join(tempfile.mkdtemp(), "admin.db")
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "homepage-editor-test",
            "ADMIN_DATABASE": database,
        }
    )
    client = app.test_client()
    client.post(
        "/admin/login",
        data={"username": "admin", "password": "aluye2026"},
    )
    client.post(
        "/admin/homepage",
        data={
            "announcement_1": "Message one",
            "announcement_2": "Message two",
            "announcement_3": "Message three",
            "hero_headline": "Edited hero",
            "hero_subheadline": "Edited subheadline",
            "hero_button": "Shop",
            "hero_link": "/shop",
            "new_arrivals": "on",
            "best_sellers": "on",
            "brand_story": "on",
            "ingredients": "on",
            "journal": "on",
            "signup_heading": "Join",
            "signup_subheading": "News",
            "category_order": "Men,Oil,Skin Care,Hair,Beards,African Black Soap",
            "category_men": "on",
            "category_oil": "on",
            "category_skin_care": "on",
            "category_hair": "on",
            "category_beards": "on",
        },
    )
    home = client.get("/").get_data(as_text=True)
    assert "Edited hero" in home
    category_section = home.split("Shop Aluyè", 1)[1].split("New This Season", 1)[0]
    assert category_section.find(">Men<") < category_section.find(">Oil<")
    assert ">African Black Soap<" not in category_section
