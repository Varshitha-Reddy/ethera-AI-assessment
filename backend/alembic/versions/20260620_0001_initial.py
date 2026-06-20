"""Initial production schema."""
from alembic import op
import sqlalchemy as sa

revision = "20260620_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("products", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("name", sa.String(), nullable=False), sa.Column("sku", sa.String(), nullable=False, unique=True), sa.Column("price", sa.Float(), nullable=False), sa.Column("quantity", sa.Integer(), nullable=False), sa.Column("description", sa.Text()), sa.Column("created_at", sa.DateTime(), nullable=False), sa.Column("updated_at", sa.DateTime(), nullable=False), sa.Column("is_active", sa.Boolean(), nullable=True))
    op.create_index("idx_product_sku_active", "products", ["sku", "is_active"])
    op.create_index("idx_product_created", "products", ["created_at"])
    op.create_table("customers", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("full_name", sa.String(), nullable=False), sa.Column("email", sa.String(), nullable=False, unique=True), sa.Column("phone", sa.String(), nullable=False), sa.Column("address", sa.String()), sa.Column("created_at", sa.DateTime(), nullable=False), sa.Column("updated_at", sa.DateTime(), nullable=False), sa.Column("is_active", sa.Boolean(), nullable=True))
    op.create_index("idx_customer_email_active", "customers", ["email", "is_active"])
    op.create_index("idx_customer_created", "customers", ["created_at"])
    op.create_table("orders", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id"), nullable=False), sa.Column("total_amount", sa.Float(), nullable=False), sa.Column("status", sa.String()), sa.Column("created_at", sa.DateTime(), nullable=False), sa.Column("updated_at", sa.DateTime(), nullable=False), sa.Column("payment_method", sa.String()), sa.Column("shipping_address", sa.String()), sa.Column("idempotency_key", sa.String(128), unique=True))
    op.create_index("idx_order_customer_status", "orders", ["customer_id", "status"])
    op.create_index("idx_order_created", "orders", ["created_at"])
    op.create_index("idx_order_status", "orders", ["status"])
    op.create_index("ix_orders_idempotency_key", "orders", ["idempotency_key"], unique=True)
    op.create_table("order_items", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=False), sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False), sa.Column("quantity", sa.Integer(), nullable=False), sa.Column("price", sa.Float(), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=False), sa.UniqueConstraint("order_id", "product_id", name="order_product_unique"))
    op.create_table("order_audit_logs", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=False), sa.Column("action", sa.String(), nullable=False), sa.Column("old_status", sa.String()), sa.Column("new_status", sa.String()), sa.Column("changed_at", sa.DateTime(), nullable=False), sa.Column("details", sa.Text()))
    op.create_index("idx_audit_order_created", "order_audit_logs", ["order_id", "changed_at"])
    op.create_table("outbox_events", sa.Column("id", sa.String(36), primary_key=True), sa.Column("aggregate_type", sa.String(64), nullable=False), sa.Column("aggregate_id", sa.String(64), nullable=False), sa.Column("event_type", sa.String(128), nullable=False), sa.Column("payload", sa.Text(), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=False), sa.Column("published_at", sa.DateTime()), sa.Column("attempts", sa.Integer(), nullable=False), sa.Column("last_error", sa.Text()))
    op.create_index("idx_outbox_unpublished", "outbox_events", ["published_at", "created_at"])


def downgrade() -> None:
    for table in ("outbox_events", "order_audit_logs", "order_items", "orders", "customers", "products"):
        op.drop_table(table)
