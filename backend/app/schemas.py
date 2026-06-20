"""
Schemas with pagination support for API requests and responses.
"""
from typing import Any, List, Optional
from pydantic import BaseModel, EmailStr, constr, conint, confloat, Field
from datetime import datetime

# Pagination
class PaginationParams(BaseModel):
    """Common pagination parameters."""
    skip: int = Field(0, ge=0)
    limit: int = Field(20, ge=1, le=100)

class PaginatedResponse(BaseModel):
    """Generic paginated response wrapper."""
    items: List[Any]
    total: int
    skip: int
    limit: int
    has_more: bool

# Product schemas
class ProductBase(BaseModel):
    name: str
    sku: str
    price: confloat(ge=0)
    quantity: conint(ge=0)
    description: Optional[str] = None

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    sku: Optional[str] = None
    price: Optional[confloat(ge=0)] = None
    quantity: Optional[conint(ge=0)] = None
    description: Optional[str] = None

class ProductOut(ProductBase):
    id: int
    created_at: datetime
    updated_at: datetime
    is_active: bool

    class Config:
        from_attributes = True

# Customer schemas
class CustomerBase(BaseModel):
    full_name: str
    email: EmailStr
    phone: str
    address: Optional[str] = None

class CustomerCreate(CustomerBase):
    pass

class CustomerUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None

class CustomerOut(CustomerBase):
    id: int
    created_at: datetime
    updated_at: datetime
    is_active: bool

    class Config:
        from_attributes = True

# Order schemas
class OrderItemCreate(BaseModel):
    product_id: int
    quantity: conint(gt=0)

class OrderItemOut(BaseModel):
    product_id: int
    quantity: int
    price: float
    product_name: str

    class Config:
        from_attributes = True

class OrderCreate(BaseModel):
    customer_id: int
    items: List[OrderItemCreate] = Field(min_length=1, max_length=100)
    payment_method: Optional[str] = None
    shipping_address: Optional[str] = None

class OrderUpdate(BaseModel):
    status: Optional[str] = None
    payment_method: Optional[str] = None
    shipping_address: Optional[str] = None

class OrderOut(BaseModel):
    id: int
    customer_id: int
    customer_name: str
    total_amount: float
    status: str
    items: List[OrderItemOut]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class OrderWithAuditOut(OrderOut):
    """Order with audit log information."""
    audit_logs: List['OrderAuditLogOut'] = Field(default_factory=list)

class OrderAuditLogOut(BaseModel):
    id: int
    action: str
    old_status: Optional[str]
    new_status: Optional[str]
    changed_at: datetime
    details: Optional[str]

    class Config:
        from_attributes = True

# Paginated responses
class PaginatedProductsResponse(BaseModel):
    items: List[ProductOut]
    total: int
    skip: int
    limit: int
    has_more: bool

class PaginatedCustomersResponse(BaseModel):
    items: List[CustomerOut]
    total: int
    skip: int
    limit: int
    has_more: bool

class PaginatedOrdersResponse(BaseModel):
    items: List[OrderOut]
    total: int
    skip: int
    limit: int
    has_more: bool

# Batch operations
class BulkProductCreate(BaseModel):
    products: List[ProductCreate]

class BulkProductCreateResponse(BaseModel):
    created: int
    failed: int
    errors: List[str] = Field(default_factory=list)

# Analytics
class DashboardStats(BaseModel):
    total_products: int
    total_customers: int
    total_orders: int
    low_stock_products: int
    total_revenue: float
    orders_today: int
    avg_order_value: float

# Error response
class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
