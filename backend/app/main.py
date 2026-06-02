import os
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from .database import engine, get_db
from . import models, schemas

models.Base.metadata.create_all(bind=engine)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/products", response_model=schemas.ProductOut, status_code=status.HTTP_201_CREATED)
def create_product(product: schemas.ProductCreate, db: Session = Depends(get_db)):
    existing = db.query(models.Product).filter(models.Product.sku == product.sku).first()
    if existing:
        raise HTTPException(status_code=409, detail="Product SKU already exists")
    if product.quantity < 0:
        raise HTTPException(status_code=400, detail="Quantity cannot be negative")
    item = models.Product(**product.dict())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item

@app.get("/products", response_model=list[schemas.ProductOut])
def list_products(db: Session = Depends(get_db)):
    return db.query(models.Product).all()

@app.get("/products/{product_id}", response_model=schemas.ProductOut)
def get_product(product_id: int, db: Session = Depends(get_db)):
    item = db.get(models.Product, product_id)
    if not item:
        raise HTTPException(status_code=404, detail="Product not found")
    return item

@app.put("/products/{product_id}", response_model=schemas.ProductOut)
def update_product(product_id: int, payload: schemas.ProductUpdate, db: Session = Depends(get_db)):
    item = db.get(models.Product, product_id)
    if not item:
        raise HTTPException(status_code=404, detail="Product not found")
    if payload.sku and payload.sku != item.sku:
        dup = db.query(models.Product).filter(models.Product.sku == payload.sku).first()
        if dup:
            raise HTTPException(status_code=409, detail="Product SKU already exists")
    for field, value in payload.dict(exclude_unset=True).items():
        setattr(item, field, value)
    if item.quantity < 0:
        raise HTTPException(status_code=400, detail="Quantity cannot be negative")
    db.commit()
    db.refresh(item)
    return item

@app.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(product_id: int, db: Session = Depends(get_db)):
    item = db.get(models.Product, product_id)
    if not item:
        raise HTTPException(status_code=404, detail="Product not found")
    db.delete(item)
    db.commit()
    return

@app.post("/customers", response_model=schemas.CustomerOut, status_code=status.HTTP_201_CREATED)
def create_customer(customer: schemas.CustomerCreate, db: Session = Depends(get_db)):
    existing = db.query(models.Customer).filter(models.Customer.email == customer.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already in use")
    cust = models.Customer(**customer.dict())
    db.add(cust)
    db.commit()
    db.refresh(cust)
    return cust

@app.get("/customers", response_model=list[schemas.CustomerOut])
def list_customers(db: Session = Depends(get_db)):
    return db.query(models.Customer).all()

@app.get("/customers/{customer_id}", response_model=schemas.CustomerOut)
def get_customer(customer_id: int, db: Session = Depends(get_db)):
    cust = db.get(models.Customer, customer_id)
    if not cust:
        raise HTTPException(status_code=404, detail="Customer not found")
    return cust

@app.delete("/customers/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_customer(customer_id: int, db: Session = Depends(get_db)):
    cust = db.get(models.Customer, customer_id)
    if not cust:
        raise HTTPException(status_code=404, detail="Customer not found")
    db.delete(cust)
    db.commit()
    return

@app.post("/orders", response_model=schemas.OrderOut, status_code=status.HTTP_201_CREATED)
def create_order(order: schemas.OrderCreate, db: Session = Depends(get_db)):
    customer = db.get(models.Customer, order.customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    if not order.items:
        raise HTTPException(status_code=400, detail="Order must have at least one item")
    total = 0.0
    items = []
    for item_data in order.items:
        product = db.get(models.Product, item_data.product_id)
        if not product:
            raise HTTPException(status_code=404, detail=f"Product {item_data.product_id} not found")
        if item_data.quantity > product.quantity:
            raise HTTPException(status_code=400, detail=f"Insufficient stock for product {product.name}")
        product.quantity -= item_data.quantity
        line_total = product.price * item_data.quantity
        total += line_total
        items.append(models.OrderItem(product_id=product.id, quantity=item_data.quantity, price=product.price))
    new_order = models.Order(customer_id=customer.id, total_amount=round(total, 2), items=items)
    db.add(new_order)
    db.commit()
    db.refresh(new_order)
    return new_order

@app.get("/orders", response_model=list[schemas.OrderOut])
def list_orders(db: Session = Depends(get_db)):
    orders = db.query(models.Order).all()
    result = []
    for order in orders:
        result.append(order)
    return result

@app.get("/orders/{order_id}", response_model=schemas.OrderOut)
def get_order(order_id: int, db: Session = Depends(get_db)):
    order = db.get(models.Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order

@app.delete("/orders/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_order(order_id: int, db: Session = Depends(get_db)):
    order = db.get(models.Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    for item in order.items:
        product = db.get(models.Product, item.product_id)
        if product:
            product.quantity += item.quantity
    db.delete(order)
    db.commit()
    return
