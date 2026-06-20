"""Async unit/integration coverage for API boundaries and business transactions."""
import pytest
from sqlalchemy import func, select

from app.database import AsyncSessionLocal
from app.models import Order, OutboxEvent, Product

pytestmark = pytest.mark.asyncio


async def product(client, headers, sku="TEST-001", quantity=10, price=12.5):
    response = await client.post(
        "/products",
        json={"name": "Test product", "sku": sku, "price": price, "quantity": quantity},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


async def customer(client, headers, email="person@example.com"):
    response = await client.post(
        "/customers",
        json={"full_name": "Test Person", "email": email, "phone": "+1-555-0100"},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_health_is_public(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


async def test_protected_route_rejects_missing_token(client):
    response = await client.get("/products")
    assert response.status_code == 401


async def test_rbac_viewer_cannot_write(client, viewer_headers):
    response = await client.post(
        "/products", json={"name": "No", "sku": "NO", "price": 1, "quantity": 1}, headers=viewer_headers
    )
    assert response.status_code == 403


async def test_bootstrap_login_issues_jwt(client):
    response = await client.post("/auth/token", data={"username": "admin", "password": "change-me"})
    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"


async def test_create_and_get_product(client, editor_headers, viewer_headers):
    created = await product(client, editor_headers)
    response = await client.get(f"/products/{created['id']}", headers=viewer_headers)
    assert response.status_code == 200
    assert response.json()["sku"] == "TEST-001"


async def test_duplicate_sku_is_conflict(client, editor_headers):
    await product(client, editor_headers)
    response = await client.post(
        "/products",
        json={"name": "Duplicate", "sku": "TEST-001", "price": 1, "quantity": 1},
        headers=editor_headers,
    )
    assert response.status_code == 409


async def test_product_validation_and_pagination(client, editor_headers, viewer_headers):
    invalid = await client.post(
        "/products", json={"name": "Bad", "sku": "BAD", "price": 1, "quantity": -1}, headers=editor_headers
    )
    assert invalid.status_code == 422
    for n in range(3):
        await product(client, editor_headers, f"SKU-{n}")
    page = await client.get("/products?skip=1&limit=1", headers=viewer_headers)
    assert page.status_code == 200
    assert page.json()["total"] == 3
    assert page.json()["has_more"] is True


async def test_customer_email_validation_and_duplicate(client, editor_headers):
    invalid = await client.post(
        "/customers", json={"full_name": "Bad", "email": "not-email", "phone": "1"}, headers=editor_headers
    )
    assert invalid.status_code == 422
    await customer(client, editor_headers)
    duplicate = await client.post(
        "/customers",
        json={"full_name": "Other", "email": "person@example.com", "phone": "2"},
        headers=editor_headers,
    )
    assert duplicate.status_code == 409


async def test_order_is_atomic_reduces_stock_and_writes_outbox(client, editor_headers):
    prod = await product(client, editor_headers, quantity=10, price=7.25)
    cust = await customer(client, editor_headers)
    response = await client.post(
        "/orders",
        json={"customer_id": cust["id"], "items": [{"product_id": prod["id"], "quantity": 3}]},
        headers={**editor_headers, "Idempotency-Key": "checkout-1"},
    )
    assert response.status_code == 201, response.text
    assert response.json()["total_amount"] == 21.75
    async with AsyncSessionLocal() as db:
        stored = await db.get(Product, prod["id"])
        outbox_count = await db.scalar(select(func.count(OutboxEvent.id)))
        assert stored.quantity == 7
        assert outbox_count == 1


async def test_insufficient_stock_rolls_back(client, editor_headers):
    prod = await product(client, editor_headers, quantity=1)
    cust = await customer(client, editor_headers)
    response = await client.post(
        "/orders",
        json={"customer_id": cust["id"], "items": [{"product_id": prod["id"], "quantity": 2}]},
        headers=editor_headers,
    )
    assert response.status_code == 400
    async with AsyncSessionLocal() as db:
        assert (await db.get(Product, prod["id"])).quantity == 1
        assert await db.scalar(select(func.count(Order.id))) == 0


async def test_idempotency_key_returns_original_order(client, editor_headers):
    prod = await product(client, editor_headers, quantity=10)
    cust = await customer(client, editor_headers)
    payload = {"customer_id": cust["id"], "items": [{"product_id": prod["id"], "quantity": 2}]}
    headers = {**editor_headers, "Idempotency-Key": "stable-retry-key"}
    first = await client.post("/orders", json=payload, headers=headers)
    second = await client.post("/orders", json=payload, headers=headers)
    assert first.status_code == second.status_code == 201
    assert first.json()["id"] == second.json()["id"]
    async with AsyncSessionLocal() as db:
        assert (await db.get(Product, prod["id"])).quantity == 8


async def test_cancel_restores_inventory_once(client, editor_headers, admin_headers):
    prod = await product(client, editor_headers, quantity=5)
    cust = await customer(client, editor_headers)
    order = await client.post(
        "/orders",
        json={"customer_id": cust["id"], "items": [{"product_id": prod["id"], "quantity": 2}]},
        headers=editor_headers,
    )
    order_id = order.json()["id"]
    assert (await client.delete(f"/orders/{order_id}", headers=admin_headers)).status_code == 204
    assert (await client.delete(f"/orders/{order_id}", headers=admin_headers)).status_code == 409
    async with AsyncSessionLocal() as db:
        assert (await db.get(Product, prod["id"])).quantity == 5


async def test_dashboard_aggregates_data(client, editor_headers, viewer_headers):
    await product(client, editor_headers, quantity=2)
    await customer(client, editor_headers)
    response = await client.get("/analytics/dashboard", headers=viewer_headers)
    assert response.status_code == 200
    assert response.json()["total_products"] == 1
    assert response.json()["low_stock_products"] == 1
