from typing import List, Optional
from pydantic import BaseModel, EmailStr, constr, conint, confloat

class ProductBase(BaseModel):
    name: str
    sku: str
    price: confloat(ge=0)
    quantity: conint(ge=0)

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    name: Optional[str]
    sku: Optional[str]
    price: Optional[confloat(ge=0)]
    quantity: Optional[conint(ge=0)]

class ProductOut(ProductBase):
    id: int

    class Config:
        orm_mode = True

class CustomerBase(BaseModel):
    full_name: str
    email: EmailStr
    phone: str

class CustomerCreate(CustomerBase):
    pass

class CustomerOut(CustomerBase):
    id: int

    class Config:
        orm_mode = True

class OrderItemCreate(BaseModel):
    product_id: int
    quantity: conint(gt=0)

class OrderCreate(BaseModel):
    customer_id: int
    items: List[OrderItemCreate]

class OrderItemOut(BaseModel):
    product_id: int
    quantity: int
    price: float
    product_name: str

    class Config:
        orm_mode = True

class OrderOut(BaseModel):
    id: int
    customer_id: int
    customer_name: str
    total_amount: float
    items: List[OrderItemOut]

    class Config:
        orm_mode = True
