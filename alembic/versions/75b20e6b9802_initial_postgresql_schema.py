"""Initial PostgreSQL schema

Revision ID: 75b20e6b9802
Revises: 
Create Date: 2026-09-02 20:24:48.872046

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '75b20e6b9802'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. admin_users
    op.create_table(
        'admin_users',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('username', sa.String(length=255), nullable=False, unique=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=100), nullable=False, server_default='Super Admin'),
    )

    # 2. products
    op.create_table(
        'products',
        sa.Column('slug', sa.String(length=255), primary_key=True),
        sa.Column('data', sa.Text(), nullable=False),
        sa.Column('stock', sa.Integer(), nullable=False, server_default='20'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='active'),
        sa.Column('updated_at', sa.String(length=100), nullable=False),
    )

    # 3. orders
    op.create_table(
        'orders',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('order_number', sa.String(length=255), nullable=False, unique=True),
        sa.Column('customer_name', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('items', sa.Text(), nullable=False),
        sa.Column('total', sa.Float(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='Pending'),
        sa.Column('tracking', sa.String(length=255), nullable=True, server_default=''),
        sa.Column('payment_method', sa.String(length=100), nullable=True, server_default='Online payment'),
        sa.Column('created_at', sa.String(length=100), nullable=False),
        sa.Column('updated_at', sa.String(length=100), nullable=False),
        sa.Column('transaction_id', sa.String(length=255), nullable=True, server_default=''),
        sa.Column('shipping_fee', sa.Float(), nullable=True, server_default='0'),
        sa.Column('phone', sa.String(length=100), nullable=True, server_default=''),
    )

    # 4. messages
    op.create_table(
        'messages',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('subject', sa.String(length=255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='unread'),
        sa.Column('created_at', sa.String(length=100), nullable=False),
    )

    # 5. notifications
    op.create_table(
        'notifications',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('kind', sa.String(length=100), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('detail', sa.Text(), nullable=False),
        sa.Column('is_read', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.String(length=100), nullable=False),
        sa.Column('related_type', sa.String(length=100), nullable=True, server_default=''),
        sa.Column('related_id', sa.String(length=255), nullable=True, server_default=''),
        sa.Column('archived', sa.Integer(), nullable=True, server_default='0'),
    )

    # 6. settings
    op.create_table(
        'settings',
        sa.Column('key', sa.String(length=255), primary_key=True),
        sa.Column('value', sa.Text(), nullable=False),
        sa.Column('updated_at', sa.String(length=100), nullable=False),
    )

    # 7. discounts
    op.create_table(
        'discounts',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('code', sa.String(length=100), nullable=False, unique=True),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('value', sa.Float(), nullable=False),
        sa.Column('minimum', sa.Float(), nullable=True, server_default='0'),
        sa.Column('expiry', sa.String(length=100), nullable=True),
        sa.Column('usage_limit', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('used', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('enabled', sa.Integer(), nullable=True, server_default='1'),
    )

    # 8. shipping_zones
    op.create_table(
        'shipping_zones',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('rate', sa.Float(), nullable=False),
        sa.Column('threshold', sa.Float(), nullable=False),
        sa.Column('delivery_days', sa.String(length=100), nullable=False),
        sa.Column('enabled', sa.Integer(), nullable=True, server_default='1'),
        sa.Column('postal_prefixes', sa.Text(), nullable=True, server_default=''),
    )

    # 9. blog_posts
    op.create_table(
        'blog_posts',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('slug', sa.String(length=255), nullable=False, unique=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.String(length=100), nullable=False),
    )

    # 10. analytics
    op.create_table(
        'analytics',
        sa.Column('path', sa.String(length=255), primary_key=True),
        sa.Column('views', sa.Integer(), nullable=False, server_default='0'),
    )

    # 11. product_events
    op.create_table(
        'product_events',
        sa.Column('slug', sa.String(length=255), primary_key=True),
        sa.Column('views', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('cart_adds', sa.Integer(), nullable=False, server_default='0'),
    )

    # 12. activity
    op.create_table(
        'activity',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('username', sa.String(length=255), nullable=False),
        sa.Column('action', sa.Text(), nullable=False),
        sa.Column('created_at', sa.String(length=100), nullable=False),
    )

    # 13. subscribers
    op.create_table(
        'subscribers',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('email', sa.String(length=255), nullable=False, unique=True),
        sa.Column('created_at', sa.String(length=100), nullable=False),
        sa.Column('source', sa.String(length=100), nullable=True, server_default='website'),
    )

    # 14. reviews
    op.create_table(
        'reviews',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('product_slug', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('photo', sa.String(length=500), nullable=True, server_default=''),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='pending'),
        sa.Column('created_at', sa.String(length=100), nullable=False),
    )

    # 15. wishlist
    op.create_table(
        'wishlist',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('product_slug', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.String(length=100), nullable=False),
    )

    # 16. ugc_photos
    op.create_table(
        'ugc_photos',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('image', sa.String(length=500), nullable=False),
        sa.Column('customer_name', sa.String(length=255), nullable=False),
        sa.Column('product_slug', sa.String(length=255), nullable=True, server_default=''),
        sa.Column('active', sa.Integer(), nullable=True, server_default='1'),
        sa.Column('sort_order', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('created_at', sa.String(length=100), nullable=False),
    )

    # 17. abandoned_carts
    op.create_table(
        'abandoned_carts',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('items', sa.Text(), nullable=False),
        sa.Column('total', sa.Float(), nullable=False),
        sa.Column('reminded', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('created_at', sa.String(length=100), nullable=False),
    )

    # 18. return_requests
    op.create_table(
        'return_requests',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('reference', sa.String(length=255), nullable=False, unique=True),
        sa.Column('order_number', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('items', sa.Text(), nullable=False),
        sa.Column('reason', sa.String(length=255), nullable=False),
        sa.Column('details', sa.Text(), nullable=True, server_default=''),
        sa.Column('refund_method', sa.String(length=100), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='Pending'),
        sa.Column('admin_note', sa.Text(), nullable=True, server_default=''),
        sa.Column('created_at', sa.String(length=100), nullable=False),
    )

    # 19. waitlist
    op.create_table(
        'waitlist',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('product_slug', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.String(length=100), nullable=False),
        sa.UniqueConstraint('product_slug', 'email', name='uq_waitlist_product_email'),
    )

    # 20. referrals
    op.create_table(
        'referrals',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('referrer_code', sa.String(length=255), nullable=False),
        sa.Column('referred_email', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='pending'),
        sa.Column('created_at', sa.String(length=100), nullable=False),
    )

    # 21. loyalty_points
    op.create_table(
        'loyalty_points',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('action', sa.String(length=255), nullable=False),
        sa.Column('points', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.String(length=100), nullable=False),
    )

    # 22. quiz_responses
    op.create_table(
        'quiz_responses',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('skin_type', sa.String(length=100), nullable=True),
        sa.Column('skin_concern', sa.String(length=100), nullable=True),
        sa.Column('hair_concern', sa.String(length=100), nullable=True),
        sa.Column('beard', sa.String(length=100), nullable=True),
        sa.Column('budget', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.String(length=100), nullable=False),
    )

    # 23. message_replies (FK -> messages.id)
    op.create_table(
        'message_replies',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('message_id', sa.Integer(), sa.ForeignKey('messages.id'), nullable=False),
        sa.Column('reply_text', sa.Text(), nullable=False),
        sa.Column('replied_by', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.String(length=100), nullable=False),
    )

    # 24. message_drafts (FK -> messages.id)
    op.create_table(
        'message_drafts',
        sa.Column('message_id', sa.Integer(), sa.ForeignKey('messages.id'), primary_key=True),
        sa.Column('draft_text', sa.Text(), nullable=False),
        sa.Column('updated_at', sa.String(length=100), nullable=False),
    )

    # 25. customers
    op.create_table(
        'customers',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('first_name', sa.String(length=255), nullable=False),
        sa.Column('last_name', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False, unique=True),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('phone', sa.String(length=100), nullable=True, server_default=''),
        sa.Column('address', sa.Text(), nullable=True, server_default=''),
        sa.Column('city', sa.String(length=255), nullable=True, server_default=''),
        sa.Column('state', sa.String(length=255), nullable=True, server_default=''),
        sa.Column('postal_code', sa.String(length=100), nullable=True, server_default=''),
        sa.Column('country', sa.String(length=255), nullable=True, server_default=''),
        sa.Column('created_at', sa.String(length=100), nullable=False),
    )

    # 26. stock_log
    op.create_table(
        'stock_log',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('product_slug', sa.String(length=255), nullable=False),
        sa.Column('change_qty', sa.Integer(), nullable=False),
        sa.Column('reason', sa.String(length=255), nullable=False),
        sa.Column('reference', sa.String(length=255), nullable=True, server_default=''),
        sa.Column('stock_after', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.String(length=100), nullable=False),
    )

    # 27. gift_cards
    op.create_table(
        'gift_cards',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('code', sa.String(length=100), nullable=False, unique=True),
        sa.Column('original_value', sa.Float(), nullable=False),
        sa.Column('remaining', sa.Float(), nullable=False),
        sa.Column('from_name', sa.String(length=255), nullable=True, server_default=''),
        sa.Column('to_name', sa.String(length=255), nullable=True, server_default=''),
        sa.Column('to_email', sa.String(length=255), nullable=True, server_default=''),
        sa.Column('message', sa.Text(), nullable=True, server_default=''),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='active'),
        sa.Column('created_at', sa.String(length=100), nullable=False),
        sa.Column('expires_at', sa.String(length=100), nullable=False),
    )


def downgrade() -> None:
    # Dependency-safe reverse order drop
    op.drop_table('gift_cards')
    op.drop_table('stock_log')
    op.drop_table('customers')
    op.drop_table('message_drafts')
    op.drop_table('message_replies')
    op.drop_table('quiz_responses')
    op.drop_table('loyalty_points')
    op.drop_table('referrals')
    op.drop_table('waitlist')
    op.drop_table('return_requests')
    op.drop_table('abandoned_carts')
    op.drop_table('ugc_photos')
    op.drop_table('wishlist')
    op.drop_table('reviews')
    op.drop_table('subscribers')
    op.drop_table('activity')
    op.drop_table('product_events')
    op.drop_table('analytics')
    op.drop_table('blog_posts')
    op.drop_table('shipping_zones')
    op.drop_table('discounts')
    op.drop_table('settings')
    op.drop_table('notifications')
    op.drop_table('messages')
    op.drop_table('orders')
    op.drop_table('products')
    op.drop_table('admin_users')
