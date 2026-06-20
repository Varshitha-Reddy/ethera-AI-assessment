from sqlalchemy import Column, Integer, String, Float, ForeignKey, UniqueConstraint, DateTime, Boolean, Index, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base
from datetime import datetime

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    sku = Column(String, nullable=False, unique=True, index=True)
    price = Column(Float, nullable=False)
    quantity = Column(Integer, nullable=False, default=0)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    is_active = Column(Boolean, default=True, index=True)
    
    # Relationships
    order_items = relationship("OrderItem", back_populates="product", cascade="all, delete-orphan")
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_product_sku_active', 'sku', 'is_active'),
        Index('idx_product_created', 'created_at'),
    )

class Customer(Base):
    __tablename__ = "customers"
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False, index=True)
    email = Column(String, nullable=False, unique=True, index=True)
    phone = Column(String, nullable=False, index=True)
    address = Column(String, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    is_active = Column(Boolean, default=True, index=True)
    
    # Relationships
    orders = relationship("Order", back_populates="customer", cascade="all, delete-orphan")
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_customer_email_active', 'email', 'is_active'),
        Index('idx_customer_created', 'created_at'),
    )

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    total_amount = Column(Float, nullable=False)
    status = Column(String, default="pending", index=True)  # pending, completed, cancelled
    created_at = Column(DateTime, default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    payment_method = Column(String, nullable=True)
    shipping_address = Column(String, nullable=True)
    idempotency_key = Column(String(128), nullable=True, unique=True, index=True)
    
    # Relationships
    customer = relationship("Customer", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    audit_logs = relationship("OrderAuditLog", back_populates="order", cascade="all, delete-orphan")

    @property
    def customer_name(self):
        return self.customer.full_name if self.customer else ""
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_order_customer_status', 'customer_id', 'status'),
        Index('idx_order_created', 'created_at'),
        Index('idx_order_status', 'status'),
    )

class OrderItem(Base):
    __tablename__ = "order_items"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    # Relationships
    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")
    
    __table_args__ = (
        UniqueConstraint("order_id", "product_id", name="order_product_unique"),
        Index('idx_orderitem_order', 'order_id'),
        Index('idx_orderitem_product', 'product_id'),
    )

    @property
    def product_name(self):
        return self.product.name if self.product else ""

class OrderAuditLog(Base):
    """Track all changes to orders for compliance and debugging."""
    __tablename__ = "order_audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    action = Column(String, nullable=False)  # created, updated, cancelled
    old_status = Column(String, nullable=True)
    new_status = Column(String, nullable=True)
    changed_at = Column(DateTime, default=func.now(), nullable=False, index=True)
    details = Column(Text, nullable=True)
    
    # Relationships
    order = relationship("Order", back_populates="audit_logs")
    
    __table_args__ = (
        Index('idx_audit_order_created', 'order_id', 'changed_at'),
    )


class OutboxEvent(Base):
    """An event committed atomically with the business transaction."""
    __tablename__ = "outbox_events"
    id = Column(String(36), primary_key=True)
    aggregate_type = Column(String(64), nullable=False, index=True)
    aggregate_id = Column(String(64), nullable=False, index=True)
    event_type = Column(String(128), nullable=False, index=True)
    payload = Column(Text, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False, index=True)
    published_at = Column(DateTime, nullable=True, index=True)
    attempts = Column(Integer, nullable=False, default=0)
    last_error = Column(Text, nullable=True)

    __table_args__ = (
        Index("idx_outbox_unpublished", "published_at", "created_at"),
    )
