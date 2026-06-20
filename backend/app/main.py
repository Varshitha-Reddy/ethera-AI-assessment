"""
Async FastAPI application with optimizations for production.
Includes pagination, caching, Kafka events, and error handling.
"""
from __future__ import annotations
import logging
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, status, Query, Header
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from .database import get_db, get_read_db, init_db
from .cache import cache_manager
from .events import event_bus
from . import models, schemas
from .config import settings
from .security import (
    Principal, admin, authenticate_bootstrap_user, create_access_token, editor, viewer
)
from .rate_limit import RateLimitMiddleware
from .observability import configure_observability
from .outbox import add_event, dispatch_pending

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("Starting up Ethera application...")
    
    # Initialize database
    await init_db()
    
    # Connect to Redis cache
    await cache_manager.connect()
    
    # Connect to Kafka event bus
    await event_bus.connect()
    stop_dispatcher = asyncio.Event()

    async def outbox_worker():
        while not stop_dispatcher.is_set():
            try:
                if settings.enable_kafka:
                    await dispatch_pending()
            except Exception:
                logger.exception("Outbox dispatch cycle failed")
            try:
                await asyncio.wait_for(stop_dispatcher.wait(), timeout=2)
            except asyncio.TimeoutError:
                pass

    dispatcher_task = asyncio.create_task(outbox_worker())
    
    logger.info("Application startup complete")
    yield
    
    logger.info("Shutting down application...")
    stop_dispatcher.set()
    await dispatcher_task
    
    # Disconnect from external services
    await cache_manager.disconnect()
    await event_bus.disconnect()
    
    logger.info("Application shutdown complete")

# Create FastAPI app
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description=settings.api_description,
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RateLimitMiddleware)
configure_observability(app)

# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.api_version,
    }

@app.get("/ready", tags=["Health"])
async def readiness_check(db: AsyncSession = Depends(get_db)):
    await db.execute(select(1))
    return {"status": "ready"}

@app.post("/auth/token", tags=["Auth"])
async def issue_token(form: OAuth2PasswordRequestForm = Depends()):
    principal = authenticate_bootstrap_user(form.username, form.password)
    if principal is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {
        "access_token": create_access_token(principal.subject, principal.role),
        "token_type": "bearer",
        "expires_in": settings.jwt_expiration_minutes * 60,
    }

# ============================================================================
# PRODUCT ENDPOINTS
# ============================================================================

@app.post("/products", response_model=schemas.ProductOut, status_code=status.HTTP_201_CREATED, tags=["Products"])
async def create_product(product: schemas.ProductCreate, db: AsyncSession = Depends(get_db), _: Principal = Depends(editor)):
    """Create a new product."""
    logger.info(f"Creating product with SKU: {product.sku}")
    
    # Check for duplicate SKU
    stmt = select(models.Product).where(models.Product.sku == product.sku)
    existing = await db.execute(stmt)
    if existing.scalars().first():
        logger.warning(f"Product SKU already exists: {product.sku}")
        raise HTTPException(status_code=409, detail="Product SKU already exists")
    
    if product.quantity < 0:
        raise HTTPException(status_code=400, detail="Quantity cannot be negative")
    
    item = models.Product(**product.dict())
    db.add(item)
    await db.commit()
    await db.refresh(item)
    
    # Invalidate cache
    await cache_manager.clear_pattern("products:*")
    
    logger.info(f"Product created: {item.id}")
    return item

@app.get("/products", response_model=schemas.PaginatedProductsResponse, tags=["Products"])
async def list_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    is_active: bool = Query(True),
    db: AsyncSession = Depends(get_read_db),
    _: Principal = Depends(viewer),
):
    """List all products with pagination."""
    cache_key = f"products:{skip}:{limit}:{is_active}"
    
    # Try cache first
    cached = await cache_manager.get(cache_key)
    if cached:
        logger.info("Cache hit for products")
        return cached
    
    # Query database
    stmt = select(models.Product).where(models.Product.is_active == is_active).offset(skip).limit(limit)
    result = await db.execute(stmt)
    items = result.scalars().all()
    
    # Get total count
    count_stmt = select(func.count(models.Product.id)).where(models.Product.is_active == is_active)
    count_result = await db.execute(count_stmt)
    total = count_result.scalar() or 0
    
    response = schemas.PaginatedProductsResponse(
        items=items,
        total=total,
        skip=skip,
        limit=limit,
        has_more=(skip + limit) < total
    )
    
    # Cache response
    await cache_manager.set(cache_key, response.dict(), ttl=300)
    
    return response

@app.get("/products/{product_id}", response_model=schemas.ProductOut, tags=["Products"])
async def get_product(product_id: int, db: AsyncSession = Depends(get_read_db), _: Principal = Depends(viewer)):
    """Get product by ID."""
    cache_key = f"product:{product_id}"
    
    # Try cache
    cached = await cache_manager.get(cache_key)
    if cached:
        return schemas.ProductOut(**cached)
    
    item = await db.get(models.Product, product_id)
    if not item:
        logger.warning(f"Product not found: {product_id}")
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Cache product
    await cache_manager.set(cache_key, item.__dict__, ttl=600)
    
    return item

@app.put("/products/{product_id}", response_model=schemas.ProductOut, tags=["Products"])
async def update_product(
    product_id: int,
    payload: schemas.ProductUpdate,
    db: AsyncSession = Depends(get_db),
    _: Principal = Depends(editor),
):
    """Update product details."""
    logger.info(f"Updating product: {product_id}")
    
    item = await db.get(models.Product, product_id)
    if not item:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Check SKU uniqueness
    if payload.sku and payload.sku != item.sku:
        stmt = select(models.Product).where(models.Product.sku == payload.sku)
        dup_result = await db.execute(stmt)
        if dup_result.scalars().first():
            raise HTTPException(status_code=409, detail="Product SKU already exists")
    
    for field, value in payload.dict(exclude_unset=True).items():
        setattr(item, field, value)
    
    if item.quantity < 0:
        raise HTTPException(status_code=400, detail="Quantity cannot be negative")
    
    await db.commit()
    await db.refresh(item)
    
    # Invalidate cache
    await cache_manager.delete(f"product:{product_id}")
    await cache_manager.clear_pattern("products:*")
    
    logger.info(f"Product updated: {product_id}")
    return item

@app.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Products"])
async def delete_product(product_id: int, db: AsyncSession = Depends(get_db), _: Principal = Depends(admin)):
    """Delete a product (soft delete via is_active flag)."""
    logger.info(f"Deleting product: {product_id}")
    
    item = await db.get(models.Product, product_id)
    if not item:
        raise HTTPException(status_code=404, detail="Product not found")
    
    item.is_active = False
    await db.commit()
    
    # Invalidate cache
    await cache_manager.delete(f"product:{product_id}")
    await cache_manager.clear_pattern("products:*")
    
    logger.info(f"Product deleted: {product_id}")

# ============================================================================
# CUSTOMER ENDPOINTS
# ============================================================================

@app.post("/customers", response_model=schemas.CustomerOut, status_code=status.HTTP_201_CREATED, tags=["Customers"])
async def create_customer(customer: schemas.CustomerCreate, db: AsyncSession = Depends(get_db), _: Principal = Depends(editor)):
    """Create a new customer."""
    logger.info(f"Creating customer: {customer.email}")
    
    stmt = select(models.Customer).where(models.Customer.email == customer.email)
    existing = await db.execute(stmt)
    if existing.scalars().first():
        logger.warning(f"Email already exists: {customer.email}")
        raise HTTPException(status_code=409, detail="Email already in use")
    
    cust = models.Customer(**customer.dict())
    db.add(cust)
    await db.commit()
    await db.refresh(cust)
    
    await cache_manager.clear_pattern("customers:*")
    logger.info(f"Customer created: {cust.id}")
    
    return cust

@app.get("/customers", response_model=schemas.PaginatedCustomersResponse, tags=["Customers"])
async def list_customers(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    is_active: bool = Query(True),
    db: AsyncSession = Depends(get_read_db),
    _: Principal = Depends(viewer),
):
    """List all customers with pagination."""
    cache_key = f"customers:{skip}:{limit}:{is_active}"
    
    cached = await cache_manager.get(cache_key)
    if cached:
        logger.info("Cache hit for customers")
        return cached
    
    stmt = select(models.Customer).where(models.Customer.is_active == is_active).offset(skip).limit(limit)
    result = await db.execute(stmt)
    items = result.scalars().all()
    
    count_stmt = select(func.count(models.Customer.id)).where(models.Customer.is_active == is_active)
    count_result = await db.execute(count_stmt)
    total = count_result.scalar() or 0
    
    response = schemas.PaginatedCustomersResponse(
        items=items,
        total=total,
        skip=skip,
        limit=limit,
        has_more=(skip + limit) < total
    )
    
    await cache_manager.set(cache_key, response.dict(), ttl=300)
    return response

@app.get("/customers/{customer_id}", response_model=schemas.CustomerOut, tags=["Customers"])
async def get_customer(customer_id: int, db: AsyncSession = Depends(get_read_db), _: Principal = Depends(viewer)):
    """Get customer by ID."""
    cache_key = f"customer:{customer_id}"
    
    cached = await cache_manager.get(cache_key)
    if cached:
        return schemas.CustomerOut(**cached)
    
    cust = await db.get(models.Customer, customer_id)
    if not cust:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    await cache_manager.set(cache_key, cust.__dict__, ttl=600)
    return cust

@app.delete("/customers/{customer_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Customers"])
async def delete_customer(customer_id: int, db: AsyncSession = Depends(get_db), _: Principal = Depends(admin)):
    """Delete a customer (soft delete)."""
    logger.info(f"Deleting customer: {customer_id}")
    
    cust = await db.get(models.Customer, customer_id)
    if not cust:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    cust.is_active = False
    await db.commit()
    
    await cache_manager.delete(f"customer:{customer_id}")
    await cache_manager.clear_pattern("customers:*")
    
    logger.info(f"Customer deleted: {customer_id}")

# ============================================================================
# ORDER ENDPOINTS
# ============================================================================

@app.post("/orders", response_model=schemas.OrderOut, status_code=status.HTTP_201_CREATED, tags=["Orders"])
async def create_order(
    order: schemas.OrderCreate,
    db: AsyncSession = Depends(get_db),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key", max_length=128),
    _: Principal = Depends(editor),
):
    """Create a new order with inventory validation and stock reduction."""
    logger.info(f"Creating order for customer: {order.customer_id}")
    
    if idempotency_key:
        existing_result = await db.execute(
            select(models.Order)
            .options(selectinload(models.Order.customer), selectinload(models.Order.items).selectinload(models.OrderItem.product))
            .where(models.Order.idempotency_key == idempotency_key)
        )
        existing_order = existing_result.scalars().first()
        if existing_order:
            return existing_order

    # Validate customer exists
    customer = await db.get(models.Customer, order.customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    if not order.items:
        raise HTTPException(status_code=400, detail="Order must have at least one item")
    
    # Validate and reserve inventory
    total = 0.0
    items = []
    products_to_update = []
    seen_product_ids = set()
    
    for item_data in order.items:
        if item_data.product_id in seen_product_ids:
            raise HTTPException(status_code=400, detail=f"Duplicate product {item_data.product_id} in order")
        seen_product_ids.add(item_data.product_id)
        product_result = await db.execute(
            select(models.Product).where(models.Product.id == item_data.product_id).with_for_update()
        )
        product = product_result.scalars().first()
        if not product:
            logger.warning(f"Product not found: {item_data.product_id}")
            raise HTTPException(status_code=404, detail=f"Product {item_data.product_id} not found")
        
        if item_data.quantity > product.quantity:
            logger.warning(f"Insufficient stock for product {item_data.product_id}")
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient stock for product {product.name}. Available: {product.quantity}, Requested: {item_data.quantity}"
            )
        
        # Deduct from inventory
        product.quantity -= item_data.quantity
        line_total = product.price * item_data.quantity
        total += line_total
        
        items.append(models.OrderItem(
            product_id=product.id,
            product=product,
            quantity=item_data.quantity,
            price=product.price
        ))
        
        products_to_update.append(product)
        
        # Check for low stock alert
        if product.quantity <= 5:
            await event_bus.publish_inventory_low(product.id, product.name, product.quantity)
    
    # Create order
    new_order = models.Order(
        customer_id=customer.id,
        customer=customer,
        total_amount=round(total, 2),
        items=items,
        status="pending",
        payment_method=order.payment_method,
        shipping_address=order.shipping_address
        ,idempotency_key=idempotency_key
    )
    
    # Create audit log
    audit = models.OrderAuditLog(
        order=new_order,
        action="created",
        new_status="pending"
    )
    
    db.add(new_order)
    db.add(audit)
    
    # Update products (stock deduction)
    for product in products_to_update:
        db.add(product)
    
    await db.flush()
    add_event(
        db, "order", str(new_order.id), "order.created",
        {"order_id": new_order.id, "customer_id": customer.id, "total_amount": new_order.total_amount},
    )
    await db.commit()
    await db.refresh(new_order)
    
    # Invalidate cache
    await cache_manager.clear_pattern("orders:*")
    await cache_manager.clear_pattern("products:*")
    
    logger.info(f"Order created: {new_order.id}")
    return new_order

@app.get("/orders", response_model=schemas.PaginatedOrdersResponse, tags=["Orders"])
async def list_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: str = Query(None),
    db: AsyncSession = Depends(get_read_db),
    _: Principal = Depends(viewer),
):
    """List all orders with optional status filter."""
    cache_key = f"orders:{skip}:{limit}:{status}"
    
    cached = await cache_manager.get(cache_key)
    if cached:
        logger.info("Cache hit for orders")
        return cached
    
    stmt = select(models.Order).options(
        selectinload(models.Order.customer),
        selectinload(models.Order.items).selectinload(models.OrderItem.product),
    ).offset(skip).limit(limit)
    if status:
        stmt = stmt.where(models.Order.status == status)
    
    result = await db.execute(stmt)
    items = result.scalars().all()
    
    # Count total
    count_stmt = select(func.count(models.Order.id))
    if status:
        count_stmt = count_stmt.where(models.Order.status == status)
    count_result = await db.execute(count_stmt)
    total = count_result.scalar() or 0
    
    response = schemas.PaginatedOrdersResponse(
        items=items,
        total=total,
        skip=skip,
        limit=limit,
        has_more=(skip + limit) < total
    )
    
    await cache_manager.set(cache_key, response.dict(), ttl=300)
    return response

@app.get("/orders/{order_id}", response_model=schemas.OrderOut, tags=["Orders"])
async def get_order(order_id: int, db: AsyncSession = Depends(get_read_db), _: Principal = Depends(viewer)):
    """Get order details by ID."""
    cache_key = f"order:{order_id}"
    
    cached = await cache_manager.get(cache_key)
    if cached:
        return schemas.OrderOut(**cached)
    
    result = await db.execute(
        select(models.Order)
        .options(selectinload(models.Order.customer), selectinload(models.Order.items).selectinload(models.OrderItem.product))
        .where(models.Order.id == order_id)
    )
    order = result.scalars().first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status == "cancelled":
        raise HTTPException(status_code=409, detail="Order is already cancelled")
    
    await cache_manager.set(cache_key, order.__dict__, ttl=600)
    return order

@app.delete("/orders/{order_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Orders"])
async def delete_order(order_id: int, db: AsyncSession = Depends(get_db), _: Principal = Depends(admin)):
    """Cancel/delete an order and restore inventory."""
    logger.info(f"Cancelling order: {order_id}")
    
    result = await db.execute(select(models.Order).options(selectinload(models.Order.items)).where(models.Order.id == order_id))
    order = result.scalars().first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Restore inventory
    for item in order.items:
        product = await db.get(models.Product, item.product_id)
        if product:
            product.quantity += item.quantity
            db.add(product)
    
    # Update order status
    old_status = order.status
    order.status = "cancelled"
    
    # Create audit log
    audit = models.OrderAuditLog(
        order_id=order.id,
        action="cancelled",
        old_status=old_status,
        new_status="cancelled"
    )
    
    db.add(audit)
    add_event(db, "order", str(order.id), "order.cancelled", {"order_id": order.id, "customer_id": order.customer_id})
    await db.commit()
    
    # Invalidate cache
    await cache_manager.delete(f"order:{order_id}")
    await cache_manager.clear_pattern("orders:*")
    await cache_manager.clear_pattern("products:*")
    
    logger.info(f"Order cancelled: {order_id}")

# ============================================================================
# ANALYTICS & DASHBOARD
# ============================================================================

@app.get("/analytics/dashboard", response_model=schemas.DashboardStats, tags=["Analytics"])
async def get_dashboard_stats(db: AsyncSession = Depends(get_read_db), _: Principal = Depends(viewer)):
    """Get dashboard analytics."""
    cache_key = "dashboard:stats"
    
    cached = await cache_manager.get(cache_key)
    if cached:
        return schemas.DashboardStats(**cached)
    
    # Query all stats in parallel
    product_count = await db.execute(select(func.count(models.Product.id)).where(models.Product.is_active == True))
    customer_count = await db.execute(select(func.count(models.Customer.id)).where(models.Customer.is_active == True))
    order_count = await db.execute(select(func.count(models.Order.id)))
    low_stock = await db.execute(select(func.count(models.Product.id)).where(models.Product.quantity <= 5, models.Product.is_active == True))
    revenue = await db.execute(select(func.sum(models.Order.total_amount)))
    
    stats = schemas.DashboardStats(
        total_products=product_count.scalar() or 0,
        total_customers=customer_count.scalar() or 0,
        total_orders=order_count.scalar() or 0,
        low_stock_products=low_stock.scalar() or 0,
        total_revenue=revenue.scalar() or 0.0,
        orders_today=0,
        avg_order_value=0.0
    )
    
    await cache_manager.set(cache_key, stats.dict(), ttl=600)
    return stats

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Custom HTTP exception handler."""
    return JSONResponse(
        status_code=exc.status_code,
        content=schemas.ErrorResponse(
            error=exc.detail,
            detail=None
        ).model_dump(mode="json")
    )

logger.info("Ethera API initialized successfully")
