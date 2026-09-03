"""
SQLAlchemy Core Schema Definition for Aluyè Naturals.

Authoritative MetaData object defining all 27 application tables.
100% portable across SQLite (local/testing) and PostgreSQL (Neon production).
"""

from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    MetaData,
    Float,
    String,
    Table,
    Text,
    UniqueConstraint,
)

metadata = MetaData()

# 1. admin_users
admin_users = Table(
    "admin_users",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("username", String(255), unique=True, nullable=False),
    Column("name", String(255), nullable=False),
    Column("email", String(255), nullable=True),
    Column("password_hash", String(255), nullable=False),
    Column("role", String(100), nullable=False, server_default="Super Admin"),
)

# 2. products
products = Table(
    "products",
    metadata,
    Column("slug", String(255), primary_key=True),
    Column("data", Text, nullable=False),
    Column("stock", Integer, nullable=False, server_default="20"),
    Column("status", String(50), nullable=False, server_default="active"),
    Column("updated_at", String(100), nullable=False),
)

# 3. orders
orders = Table(
    "orders",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("order_number", String(255), unique=True, nullable=False),
    Column("customer_name", String(255), nullable=False),
    Column("email", String(255), nullable=True),
    Column("address", Text, nullable=True),
    Column("items", Text, nullable=False),
    Column("total", Float, nullable=False),
    Column("status", String(50), nullable=False, server_default="Pending"),
    Column("tracking", String(255), nullable=True, server_default=""),
    Column("payment_method", String(100), nullable=True, server_default="Online payment"),
    Column("created_at", String(100), nullable=False),
    Column("updated_at", String(100), nullable=False),
    Column("transaction_id", String(255), nullable=True, server_default=""),
    Column("shipping_fee", Float, nullable=True, server_default="0"),
    Column("phone", String(100), nullable=True, server_default=""),
)

# 4. messages
messages = Table(
    "messages",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("name", String(255), nullable=False),
    Column("email", String(255), nullable=False),
    Column("subject", String(255), nullable=False),
    Column("message", Text, nullable=False),
    Column("status", String(50), nullable=False, server_default="unread"),
    Column("created_at", String(100), nullable=False),
)

# 5. notifications
notifications = Table(
    "notifications",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("kind", String(100), nullable=False),
    Column("title", String(255), nullable=False),
    Column("detail", Text, nullable=False),
    Column("is_read", Integer, nullable=False, server_default="0"),
    Column("created_at", String(100), nullable=False),
    Column("related_type", String(100), nullable=True, server_default=""),
    Column("related_id", String(255), nullable=True, server_default=""),
    Column("archived", Integer, nullable=True, server_default="0"),
)

# 6. settings
settings = Table(
    "settings",
    metadata,
    Column("key", String(255), primary_key=True),
    Column("value", Text, nullable=False),
    Column("updated_at", String(100), nullable=False),
)

# 7. discounts
discounts = Table(
    "discounts",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("code", String(100), unique=True, nullable=False),
    Column("type", String(50), nullable=False),
    Column("value", Float, nullable=False),
    Column("minimum", Float, nullable=True, server_default="0"),
    Column("expiry", String(100), nullable=True),
    Column("usage_limit", Integer, nullable=True, server_default="0"),
    Column("used", Integer, nullable=True, server_default="0"),
    Column("enabled", Integer, nullable=True, server_default="1"),
)

# 8. shipping_zones
shipping_zones = Table(
    "shipping_zones",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("name", String(255), nullable=False),
    Column("rate", Float, nullable=False),
    Column("threshold", Float, nullable=False),
    Column("delivery_days", String(100), nullable=False),
    Column("enabled", Integer, nullable=True, server_default="1"),
    Column("postal_prefixes", Text, nullable=True, server_default=""),
)

# 9. blog_posts
blog_posts = Table(
    "blog_posts",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("slug", String(255), unique=True, nullable=False),
    Column("title", String(255), nullable=False),
    Column("category", String(100), nullable=False),
    Column("body", Text, nullable=False),
    Column("status", String(50), nullable=False),
    Column("created_at", String(100), nullable=False),
)

# 10. analytics
analytics = Table(
    "analytics",
    metadata,
    Column("path", String(255), primary_key=True),
    Column("views", Integer, nullable=False, server_default="0"),
)

# 11. product_events
product_events = Table(
    "product_events",
    metadata,
    Column("slug", String(255), primary_key=True),
    Column("views", Integer, nullable=False, server_default="0"),
    Column("cart_adds", Integer, nullable=False, server_default="0"),
)

# 12. activity
activity = Table(
    "activity",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("username", String(255), nullable=False),
    Column("action", Text, nullable=False),
    Column("created_at", String(100), nullable=False),
)

# 13. subscribers
subscribers = Table(
    "subscribers",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("email", String(255), unique=True, nullable=False),
    Column("created_at", String(100), nullable=False),
    Column("source", String(100), nullable=True, server_default="website"),
)

# 14. reviews
reviews = Table(
    "reviews",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("product_slug", String(255), nullable=False),
    Column("name", String(255), nullable=False),
    Column("email", String(255), nullable=False),
    Column("rating", Integer, nullable=False),
    Column("title", String(255), nullable=False),
    Column("body", Text, nullable=False),
    Column("photo", String(500), nullable=True, server_default=""),
    Column("status", String(50), nullable=False, server_default="pending"),
    Column("created_at", String(100), nullable=False),
)

# 15. wishlist
wishlist = Table(
    "wishlist",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_id", Integer, nullable=True),
    Column("product_slug", String(255), nullable=False),
    Column("created_at", String(100), nullable=False),
)

# 16. ugc_photos
ugc_photos = Table(
    "ugc_photos",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("image", String(500), nullable=False),
    Column("customer_name", String(255), nullable=False),
    Column("product_slug", String(255), nullable=True, server_default=""),
    Column("active", Integer, nullable=True, server_default="1"),
    Column("sort_order", Integer, nullable=True, server_default="0"),
    Column("created_at", String(100), nullable=False),
)

# 17. abandoned_carts
abandoned_carts = Table(
    "abandoned_carts",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("email", String(255), nullable=False),
    Column("items", Text, nullable=False),
    Column("total", Float, nullable=False),
    Column("reminded", Integer, nullable=True, server_default="0"),
    Column("created_at", String(100), nullable=False),
)

# 18. return_requests
return_requests = Table(
    "return_requests",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("reference", String(255), unique=True, nullable=False),
    Column("order_number", String(255), nullable=False),
    Column("email", String(255), nullable=False),
    Column("items", Text, nullable=False),
    Column("reason", String(255), nullable=False),
    Column("details", Text, nullable=True, server_default=""),
    Column("refund_method", String(100), nullable=False),
    Column("status", String(50), nullable=False, server_default="Pending"),
    Column("admin_note", Text, nullable=True, server_default=""),
    Column("created_at", String(100), nullable=False),
)

# 19. waitlist
waitlist = Table(
    "waitlist",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("product_slug", String(255), nullable=False),
    Column("email", String(255), nullable=False),
    Column("created_at", String(100), nullable=False),
    UniqueConstraint("product_slug", "email", name="uq_waitlist_product_email"),
)

# 20. referrals
referrals = Table(
    "referrals",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("referrer_code", String(255), nullable=False),
    Column("referred_email", String(255), nullable=True),
    Column("status", String(50), nullable=False, server_default="pending"),
    Column("created_at", String(100), nullable=False),
)

# 21. loyalty_points
loyalty_points = Table(
    "loyalty_points",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_id", Integer, nullable=False),
    Column("action", String(255), nullable=False),
    Column("points", Integer, nullable=False),
    Column("created_at", String(100), nullable=False),
)

# 22. quiz_responses
quiz_responses = Table(
    "quiz_responses",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("skin_type", String(100), nullable=True),
    Column("skin_concern", String(100), nullable=True),
    Column("hair_concern", String(100), nullable=True),
    Column("beard", String(100), nullable=True),
    Column("budget", String(100), nullable=True),
    Column("created_at", String(100), nullable=False),
)

# 23. message_replies
message_replies = Table(
    "message_replies",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("message_id", Integer, ForeignKey("messages.id"), nullable=False),
    Column("reply_text", Text, nullable=False),
    Column("replied_by", String(255), nullable=False),
    Column("created_at", String(100), nullable=False),
)

# 24. message_drafts
message_drafts = Table(
    "message_drafts",
    metadata,
    Column("message_id", Integer, ForeignKey("messages.id"), primary_key=True),
    Column("draft_text", Text, nullable=False),
    Column("updated_at", String(100), nullable=False),
)

# 25. customers
customers = Table(
    "customers",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("first_name", String(255), nullable=False),
    Column("last_name", String(255), nullable=False),
    Column("email", String(255), unique=True, nullable=False),
    Column("password_hash", String(255), nullable=False),
    Column("phone", String(100), nullable=True, server_default=""),
    Column("address", Text, nullable=True, server_default=""),
    Column("city", String(255), nullable=True, server_default=""),
    Column("state", String(255), nullable=True, server_default=""),
    Column("postal_code", String(100), nullable=True, server_default=""),
    Column("country", String(255), nullable=True, server_default=""),
    Column("created_at", String(100), nullable=False),
)

# 26. stock_log
stock_log = Table(
    "stock_log",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("product_slug", String(255), nullable=False),
    Column("change_qty", Integer, nullable=False),
    Column("reason", String(255), nullable=False),
    Column("reference", String(255), nullable=True, server_default=""),
    Column("stock_after", Integer, nullable=False),
    Column("created_at", String(100), nullable=False),
)

# 27. gift_cards
gift_cards = Table(
    "gift_cards",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("code", String(100), unique=True, nullable=False),
    Column("original_value", Float, nullable=False),
    Column("remaining", Float, nullable=False),
    Column("from_name", String(255), nullable=True, server_default=""),
    Column("to_name", String(255), nullable=True, server_default=""),
    Column("to_email", String(255), nullable=True, server_default=""),
    Column("message", Text, nullable=True, server_default=""),
    Column("status", String(50), nullable=False, server_default="active"),
    Column("created_at", String(100), nullable=False),
    Column("expires_at", String(100), nullable=False),
)
