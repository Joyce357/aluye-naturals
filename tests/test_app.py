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

    # PayPal is the only checkout path — submitting the plain form must never
    # place an order, since no payment has actually been taken.
    rejected = client.post(
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
    assert rejected.status_code == 200
    assert b"Order confirmed" not in rejected.data
    assert b"PayPal" in rejected.data


def test_paypal_checkout_completes_order_and_blocks_failed_capture(monkeypatch):
    import paypal_client

    database = os.path.join(tempfile.mkdtemp(), "admin.db")
    app = create_app({"TESTING": True, "SECRET_KEY": "paypal-test", "ADMIN_DATABASE": database})
    client = app.test_client()
    with app.app_context():
        from admin import save_setting

        save_setting(
            "settings",
            {"paypal_client": "fake-client-id", "paypal_configured": True, "paypal_sandbox": True},
        )
    monkeypatch.setenv("PAYPAL_SECRET", "fake-secret")
    monkeypatch.setattr(paypal_client, "_get_access_token", lambda settings: "fake-token")

    client.post("/cart/add/chlorophyll-whipped-shea-butter", data={"quantity": "1"})
    form = {
        "email": "paypalbuyer@example.com", "first_name": "Ada", "last_name": "Stone",
        "address": "1 Shea Lane", "apartment": "", "city": "Toronto", "postal_code": "M5H2M9",
        "country": "Canada", "phone": "", "shipping_method": "standard",
    }

    class FakeResponse:
        def __init__(self, payload):
            self._payload = payload

        def raise_for_status(self):
            pass

        def json(self):
            return self._payload

    monkeypatch.setattr(
        paypal_client.requests, "post", lambda *a, **k: FakeResponse({"id": "FAKE-ORDER"})
    )
    created = client.post("/api/paypal/create-order", data=form)
    assert created.status_code == 200
    assert created.get_json()["id"] == "FAKE-ORDER"

    monkeypatch.setattr(
        paypal_client.requests, "post",
        lambda *a, **k: FakeResponse({"status": "DECLINED"}),
    )
    declined = client.post("/api/paypal/capture-order/FAKE-ORDER", data=form)
    assert declined.status_code == 400
    assert declined.get_json()["ok"] is False

    with app.app_context():
        from admin import get_db

        assert get_db().execute(
            "SELECT 1 FROM orders WHERE email='paypalbuyer@example.com'"
        ).fetchone() is None

    monkeypatch.setattr(
        paypal_client.requests, "post", lambda *a, **k: FakeResponse({"id": "FAKE-ORDER-2"})
    )
    client.post("/api/paypal/create-order", data=form)
    monkeypatch.setattr(
        paypal_client.requests, "post",
        lambda *a, **k: FakeResponse({
            "status": "COMPLETED",
            "purchase_units": [{"payments": {"captures": [{"id": "FAKE-CAPTURE"}]}}],
        }),
    )
    captured = client.post("/api/paypal/capture-order/FAKE-ORDER-2", data=form)
    assert captured.status_code == 200
    result = captured.get_json()
    assert result["ok"] is True

    confirmation = client.get(result["redirect"])
    assert b"Order confirmed" in confirmation.data
    assert b"PayPal" in confirmation.data

    with app.app_context():
        from admin import get_db

        order = get_db().execute(
            "SELECT status, payment_method, transaction_id FROM orders WHERE email='paypalbuyer@example.com'"
        ).fetchone()
        assert order["status"] == "Paid"
        assert order["payment_method"] == "PayPal"
        assert order["transaction_id"] == "FAKE-CAPTURE"


def test_content_pages_and_catalogue_segments_render():
    app = create_app({"TESTING": True})
    client = app.test_client()

    for path in ("/about", "/contact", "/blog", "/blog/why-unrefined-shea-feels-different"):
        response = client.get(path)
        assert response.status_code == 200

    beards = client.get("/shop?category=Beards")
    black_soap = client.get("/shop?category=African+Black+Soap")
    assert b"Gentlemen" in beards.data
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
    assert 'data-price="18"' in cart
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
        "/admin/shipping",
        "/admin/discounts",
        "/admin/journal",
        "/admin/analytics",
        "/admin/account",
    ):
        assert client.get(path).status_code == 200


def test_contact_message_and_checkout_sync_to_admin(monkeypatch):
    import paypal_client

    database = os.path.join(tempfile.mkdtemp(), "admin.db")
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "admin-sync-test",
            "ADMIN_DATABASE": database,
        }
    )
    with app.app_context():
        from admin import save_setting

        save_setting(
            "settings",
            {"paypal_client": "fake-client-id", "paypal_configured": True, "paypal_sandbox": True},
        )
    monkeypatch.setenv("PAYPAL_SECRET", "fake-secret")
    monkeypatch.setattr(paypal_client, "_get_access_token", lambda settings: "fake-token")

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
    order_form = {
        "email": "order@example.com",
        "first_name": "Ada",
        "last_name": "Admin",
        "address": "1 Shea Lane",
        "apartment": "",
        "city": "Lagos",
        "postal_code": "100001",
        "country": "Nigeria",
        "shipping_method": "standard",
    }

    class FakeResponse:
        def __init__(self, payload):
            self._payload = payload

        def raise_for_status(self):
            pass

        def json(self):
            return self._payload

    monkeypatch.setattr(
        paypal_client.requests, "post", lambda *a, **k: FakeResponse({"id": "SYNC-ORDER"})
    )
    client.post("/api/paypal/create-order", data=order_form)
    monkeypatch.setattr(
        paypal_client.requests, "post",
        lambda *a, **k: FakeResponse({
            "status": "COMPLETED",
            "purchase_units": [{"payments": {"captures": [{"id": "SYNC-CAPTURE"}]}}],
        }),
    )
    client.post("/api/paypal/capture-order/SYNC-ORDER", data=order_form)

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
    restricted = client.get("/admin/shipping", follow_redirects=True)
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
            "category_order": "Beards,Oil,Skin Care,Hair,African Black Soap",
            "category_oil": "on",
            "category_skin_care": "on",
            "category_hair": "on",
            "category_beards": "on",
        },
    )
    home = client.get("/").get_data(as_text=True)
    assert "Edited hero" in home
    category_section = home.split("Shop Aluyè", 1)[1].split("New This Season", 1)[0]
    assert category_section.find(">Beards<") < category_section.find(">Oil<")
    assert ">African Black Soap<" not in category_section


def test_cron_endpoint_protection():
    app = create_app({"TESTING": False, "CRON_SECRET": "secret-cron-key-123"})
    client = app.test_client()

    # Unauthorized request without token
    unauth = client.get("/api/cron/abandoned-carts")
    assert unauth.status_code == 401

    # Rejected request with query string secret
    query_unauth = client.get("/api/cron/abandoned-carts?secret=secret-cron-key-123")
    assert query_unauth.status_code == 401

    # Authorized request with Bearer header
    auth = client.get("/api/cron/abandoned-carts", headers={"Authorization": "Bearer secret-cron-key-123"})
    assert auth.status_code == 200
    assert auth.json.get("status") == "ok"


def test_vercel_secret_and_upload_protections(monkeypatch):
    import admin
    app = create_app({"TESTING": True})
    with app.app_context():
        # Test Vercel secret save rejection
        monkeypatch.setenv("VERCEL", "1")
        try:
            admin.save_env_secret("TEST_VERCEL_VAR", "test_val")
            assert False, "Should have raised RuntimeError"
        except RuntimeError as e:
            assert "Vercel Dashboard" in str(e)

        # Test Local/Render secret save preservation
        monkeypatch.delenv("VERCEL", raising=False)
        monkeypatch.setattr(admin.Path, "write_text", lambda *a, **k: None)
        admin.save_env_secret("TEST_LOCAL_VAR", "local_val")
        assert os.environ.get("TEST_LOCAL_VAR") == "local_val"


def test_abandoned_cart_atomic_claim_concurrency():
    import admin
    import database
    app = create_app({"TESTING": True})
    with app.app_context():
        # Setup setting
        admin.save_setting("settings", {"abandoned_cart_enabled": True, "abandoned_cart_delay_hours": 0})

        # Insert 1 abandoned cart with reminded = 0
        items_json = json.dumps([{"slug": "chlorophyll-whipped-shea-butter", "quantity": 1, "price": 38.0}])
        database.execute_write(
            """INSERT INTO abandoned_carts(email, items, total, reminded, created_at)
               VALUES('concurrency-test@example.invalid', :items, 38.0, 0, '2000-01-01T00:00:00')""",
            {"items": items_json},
        )

        cart = database.fetch_one("SELECT * FROM abandoned_carts WHERE email = 'concurrency-test@example.invalid'")
        assert cart is not None and cart["reminded"] == 0

        # First worker atomic claim -> succeeds (rowcount == 1)
        claim1 = database.execute_write(
            "UPDATE abandoned_carts SET reminded = 1 WHERE id = :id AND reminded = 0",
            {"id": cart["id"]},
        )
        assert claim1["rowcount"] == 1

        # Second worker duplicate claim -> fails (rowcount == 0)
        claim2 = database.execute_write(
            "UPDATE abandoned_carts SET reminded = 1 WHERE id = :id AND reminded = 0",
            {"id": cart["id"]},
        )
        assert claim2["rowcount"] == 0

        # Cleanup
        database.execute_write("DELETE FROM abandoned_carts WHERE email = 'concurrency-test@example.invalid'")


def test_abandoned_cart_claim_release_on_email_failure(monkeypatch):
    import admin
    import database
    app = create_app({"TESTING": True})
    with app.app_context():
        admin.save_setting("settings", {"abandoned_cart_enabled": True, "abandoned_cart_delay_hours": 0})
        items_json = json.dumps([{"slug": "chlorophyll-whipped-shea-butter", "quantity": 1, "price": 38.0}])
        database.execute_write(
            """INSERT INTO abandoned_carts(email, items, total, reminded, created_at)
               VALUES('fail-test@example.invalid', :items, 38.0, 0, '2000-01-01T00:00:00')""",
            {"items": items_json},
        )

        # Mock send_mail to return failure
        monkeypatch.setattr(admin, "send_mail", lambda **kwargs: (False, "SMTP connection failed"))

        processed = admin.check_abandoned_carts(app)
        assert processed == 0

        # Verify claim was released back to 0
        cart = database.fetch_one("SELECT * FROM abandoned_carts WHERE email = 'fail-test@example.invalid'")
        assert cart["reminded"] == 0

        # Cleanup
        database.execute_write("DELETE FROM abandoned_carts WHERE email = 'fail-test@example.invalid'")


def test_no_customer_facing_discounts_on_homepage():
    app = create_app({"TESTING": True})
    client = app.test_client()
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)

    assert "Get 10% off" not in html
    assert "Get 15% off" not in html
    assert "Claim My 10% Off" not in html
    assert "Before you go" not in html
    assert 'id="exit-popup"' not in html


def test_api_subscribe_functional_and_no_discount():
    import database
    app = create_app({"TESTING": True})
    client = app.test_client()
    test_email = "regression-sub@example.invalid"

    with app.app_context():
        database.execute_write("DELETE FROM subscribers WHERE email = :email", {"email": test_email})

        resp = client.post("/api/subscribe", json={"email": test_email, "source": "footer"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data.get("ok") is True
        assert data.get("status") == "subscribed"
        assert "discount_code" not in data

        subscriber = database.fetch_one("SELECT * FROM subscribers WHERE email = :email", {"email": test_email})
        assert subscriber is not None

        # Clean up
        database.execute_write("DELETE FROM subscribers WHERE email = :email", {"email": test_email})


def test_welcome_email_template_no_discounts():
    from flask import render_template
    app = create_app({"TESTING": True})
    with app.test_request_context():
        rendered = render_template(
            "emails/welcome.html",
            first_name="Jane",
            email="jane@example.invalid",
            custom_message="We're excited to have you in our community.",
            featured_products=[],
            site_url="https://aluyenaturals.com",
        )
        assert "RITUAL10" not in rendered
        assert "RITUAL15" not in rendered
        assert "% off" not in rendered
        assert "welcome gift" not in rendered.lower()
        assert "discount" not in rendered.lower()
        assert "Valid for 30 days" not in rendered


def test_loyalty_and_ritual_club_copy_neutral():
    app = create_app({"TESTING": True})
    client = app.test_client()

    home = client.get("/").get_data(as_text=True)
    assert "exclusive offers" not in home.lower()
    assert "offers" not in home.split('id="loyalty"')[1].split('</section>')[0].lower()

    loyalty = client.get("/loyalty").get_data(as_text=True)
    assert "exclusive offers" not in loyalty.lower()
    assert "offers" not in loyalty.lower()
    assert "offers created" not in loyalty.lower()


def test_admin_discount_navigation_hidden():
    import admin
    nav_labels = [label for _, _, items in admin.NAV_GROUPS for _, label in items]
    assert "Discount Codes" not in nav_labels


def test_send_mail_plain_text_and_html_support(monkeypatch):
    import admin

    sent_messages = []

    class DummyMail:
        def __init__(self, app):
            pass

        def send(self, msg):
            sent_messages.append(msg)

    monkeypatch.setattr("flask_mail.Mail", DummyMail)

    app = create_app({"TESTING": True})
    with app.app_context():
        # Test plain-text body send
        success, error = admin.send_mail(
            subject="Plain Text Subject",
            recipients=["user@example.invalid"],
            body="Hello, this is plain text.",
        )
        assert success is True
        assert error is None
        assert len(sent_messages) == 1
        msg = sent_messages[0]
        assert msg.subject == "Plain Text Subject"
        assert msg.recipients == ["user@example.invalid"]
        assert msg.body == "Hello, this is plain text."
        assert msg.html is None

        # Test HTML send
        success, error = admin.send_mail(
            subject="HTML Subject",
            recipients=["user@example.invalid"],
            html="<p>Hello HTML</p>",
        )
        assert success is True
        assert len(sent_messages) == 2
        msg = sent_messages[1]
        assert msg.subject == "HTML Subject"
        assert msg.html == "<p>Hello HTML</p>"
        assert msg.body is None


def test_admin_message_reply_plain_text_no_html_template(monkeypatch):
    import admin
    import database

    db_path = os.path.join(tempfile.mkdtemp(), "admin.db")
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "reply-plain-text-test",
            "ADMIN_DATABASE": db_path,
        }
    )

    captured_mail = []

    def mock_send_mail(subject, recipients, html=None, reply_to=None, body=None):
        captured_mail.append({
            "subject": subject,
            "recipients": recipients,
            "html": html,
            "reply_to": reply_to,
            "body": body,
        })
        return True, None

    monkeypatch.setattr(admin, "send_mail", mock_send_mail)

    with app.app_context():
        res = database.execute_write(
            """INSERT INTO messages(name, email, subject, message, created_at, status)
               VALUES('Jane Doe', 'jane@example.invalid', 'Order Status Query', 'Where is my order?', '2026-03-01T10:00:00', 'unread')"""
        )
        msg_id = res.get("lastrowid") or 1

        client = app.test_client()
        client.post(
            "/admin/login",
            data={"username": "admin", "password": "aluye2026"},
        )

        reply_payload = {
            "action": "send",
            "reply_text": "Your order was dispatched today and is on its way.",
        }
        resp = client.post(f"/admin/messages/{msg_id}", data=reply_payload, follow_redirects=True)
        assert resp.status_code == 200

        # Verify send_mail was called with plain-text body and NO html
        assert len(captured_mail) == 1
        sent = captured_mail[0]
        assert sent["subject"] == "Re: Order Status Query"
        assert sent["recipients"] == ["jane@example.invalid"]
        assert sent["html"] is None

        # Verify body structure
        expected_body = (
            "Hi Jane Doe,\n\n"
            "Your order was dispatched today and is on its way.\n\n"
            "Warm regards,\n"
            "The Aluyè Naturals Team"
        )
        assert sent["body"] == expected_body
        assert "<" not in sent["body"]
        assert "http" not in sent["body"]

        # Verify reply was persisted in DB
        saved_reply = database.fetch_one(
            "SELECT * FROM message_replies WHERE message_id = :message_id",
            {"message_id": msg_id},
        )
        assert saved_reply is not None
        assert saved_reply["reply_text"] == "Your order was dispatched today and is on its way."

        # Verify message status was updated
        updated_msg = database.fetch_one(
            "SELECT * FROM messages WHERE id = :id",
            {"id": msg_id},
        )
        assert updated_msg["status"] == "replied"


def test_paypal_is_configured_logic(monkeypatch):
    import paypal_client

    # 1. Client ID + PAYPAL_SECRET => PayPal configured (True)
    monkeypatch.setenv("PAYPAL_SECRET", "valid-secret")
    assert paypal_client.is_configured({"paypal_client": "valid-client-id"}) is True

    # 2. Client ID without PAYPAL_SECRET => not configured (False)
    monkeypatch.delenv("PAYPAL_SECRET", raising=False)
    assert paypal_client.is_configured({"paypal_client": "valid-client-id"}) is False

    # 3. PAYPAL_SECRET without Client ID => not configured (False)
    monkeypatch.setenv("PAYPAL_SECRET", "valid-secret")
    assert paypal_client.is_configured({"paypal_client": ""}) is False
    assert paypal_client.is_configured({}) is False
    assert paypal_client.is_configured(None) is False

    # 4. Neither => not configured (False)
    monkeypatch.delenv("PAYPAL_SECRET", raising=False)
    assert paypal_client.is_configured({}) is False


def test_checkout_exposes_paypal_client_id_only_when_truly_configured(monkeypatch):
    import admin
    import database

    db_path = os.path.join(tempfile.mkdtemp(), "admin.db")
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "paypal-config-test",
            "ADMIN_DATABASE": db_path,
        }
    )
    client = app.test_client()

    # Add an item to cart so checkout page loads
    client.post("/cart/add/chlorophyll-whipped-shea-butter", data={"quantity": "1"})

    with app.app_context():
        # Case A: Stale paypal_configured=True in DB, but PAYPAL_SECRET is missing from env
        admin.save_setting("settings", {"paypal_client": "my-client-id", "paypal_configured": True})
        monkeypatch.delenv("PAYPAL_SECRET", raising=False)

        resp = client.get("/checkout")
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        assert "client-id=my-client-id" not in html
        assert 'id="paypal-button-container"' not in html
        assert ("No payment method is currently available" in html or "PayPal is not configured" in html)

        # Case B: Stale paypal_configured=False in DB, but both paypal_client and PAYPAL_SECRET exist
        admin.save_setting("settings", {"paypal_client": "real-client-id", "paypal_configured": False})
        monkeypatch.setenv("PAYPAL_SECRET", "real-secret")

        resp = client.get("/checkout")
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        assert "client-id=real-client-id" in html
        assert 'id="paypal-button-container"' in html

        # Case C: PAYPAL_SECRET exists in env, but paypal_client is empty
        admin.save_setting("settings", {"paypal_client": "", "paypal_configured": True})
        monkeypatch.setenv("PAYPAL_SECRET", "real-secret")

        resp = client.get("/checkout")
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        assert "https://www.paypal.com/sdk/js" not in html
        assert 'id="paypal-button-container"' not in html


def test_paypal_sandbox_toggle_and_admin_settings_detection(monkeypatch):
    import admin
    import database
    import paypal_client

    db_path = os.path.join(tempfile.mkdtemp(), "admin.db")
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "paypal-sandbox-test",
            "ADMIN_DATABASE": db_path,
        }
    )
    client = app.test_client()

    with app.app_context():
        # Test base_url with sandbox on/off
        assert paypal_client._base_url({"paypal_sandbox": True}) == paypal_client.SANDBOX_BASE
        assert paypal_client._base_url({"paypal_sandbox": False}) == paypal_client.LIVE_BASE
        assert paypal_client._base_url({}) == paypal_client.SANDBOX_BASE  # default is True

        # Admin login
        client.post("/admin/login", data={"username": "admin", "password": "aluye2026"})

        # 1. On Vercel simulation: submitting a secret in the form does NOT save secret or falsely connect PayPal without real env var
        monkeypatch.setenv("VERCEL", "1")
        monkeypatch.delenv("PAYPAL_SECRET", raising=False)

        resp = client.post(
            "/admin/global-settings",
            data={
                "tab": "integrations",
                "paypal_client": "my-client-id",
                "paypal_secret": "typed-secret-in-form",
                "paypal_sandbox": "on",
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        assert "On Vercel, secret environment variables must be updated in the Vercel Dashboard" in html
        settings = admin.load_setting("settings", {})
        assert settings.get("paypal_configured") is False

        # 2. When PAYPAL_SECRET is in env on Vercel:
        monkeypatch.setenv("PAYPAL_SECRET", "actual-env-secret")
        resp = client.get("/admin/global-settings?tab=integrations")
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        assert "✓ Connected" in html

        # 3. Test saving sandbox toggle off
        client.post(
            "/admin/global-settings",
            data={
                "tab": "integrations",
                "paypal_client": "my-client-id",
            },
            follow_redirects=True,
        )
        settings = admin.load_setting("settings", {})
        assert settings.get("paypal_sandbox") is False
        assert paypal_client._base_url(settings) == paypal_client.LIVE_BASE







