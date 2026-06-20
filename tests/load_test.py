"""
Load testing script using Locust.
Tests concurrent order creation, product listing, and inventory management.

Usage:
    locust -f tests/load_test.py --users=1000 --spawn-rate=50 -H http://localhost:8000
"""
import random
from locust import HttpUser, task, between
from uuid import uuid4

class EtheraBenchmarkUser(HttpUser):
    """Simulates typical Ethera user behavior."""
    
    wait_time = between(1, 3)
    
    def on_start(self):
        """Setup: Create test products and customers."""
        # Create 10 test products
        for i in range(10):
            self.client.post("/products", json={
                "name": f"Benchmark Product {i}",
                "sku": f"SKU-{uuid4()}",
                "price": random.uniform(10, 500),
                "quantity": 1000
            })
        
        # Create 5 test customers
        for i in range(5):
            self.client.post("/customers", json={
                "full_name": f"Benchmark Customer {i}",
                "email": f"customer{i}-{uuid4()}@example.com",
                "phone": f"+1-555-000{i:04d}"
            })
    
    @task(5)
    def list_products(self):
        """List products with pagination (40% of traffic)."""
        skip = random.randint(0, 100)
        self.client.get(f"/products?skip={skip}&limit=20", name="/products?skip=[int]&limit=20")
    
    @task(2)
    def get_product_detail(self):
        """Get single product detail (20% of traffic)."""
        product_id = random.randint(1, 50)
        self.client.get(f"/products/{product_id}", name="/products/[id]")
    
    @task(3)
    def create_order(self):
        """Create order with inventory validation (30% of traffic)."""
        customer_id = random.randint(1, 5)
        product_id = random.randint(1, 10)
        quantity = random.randint(1, 10)
        
        self.client.post("/orders", json={
            "customer_id": customer_id,
            "items": [
                {
                    "product_id": product_id,
                    "quantity": quantity
                }
            ]
        })
    
    @task(1)
    def list_orders(self):
        """List orders with pagination (10% of traffic)."""
        skip = random.randint(0, 100)
        self.client.get(f"/orders?skip={skip}&limit=20", name="/orders?skip=[int]&limit=20")
    
    @task(1)
    def get_dashboard_stats(self):
        """Get dashboard analytics (10% of traffic)."""
        self.client.get("/analytics/dashboard", name="/analytics/dashboard")

class EtheraPeakLoadUser(HttpUser):
    """Simulates peak load (more aggressive order creation)."""
    
    wait_time = between(0.5, 2)
    
    @task(8)
    def create_order_burst(self):
        """Burst order creation (80% of traffic)."""
        customer_id = random.randint(1, 100)
        items = []
        for _ in range(random.randint(1, 5)):
            items.append({
                "product_id": random.randint(1, 500),
                "quantity": random.randint(1, 20)
            })
        
        self.client.post("/orders", json={
            "customer_id": customer_id,
            "items": items
        })
    
    @task(2)
    def list_products_search(self):
        """Search products with caching (20% of traffic)."""
        self.client.get(f"/products?skip=0&limit=50", name="/products?cached")

class EtheraCacheTestUser(HttpUser):
    """Tests cache effectiveness."""
    
    wait_time = between(0.1, 0.5)
    
    @task(10)
    def repeat_product_lookup(self):
        """Repeatedly fetch same product to test cache."""
        product_id = 1  # Always fetch same product
        self.client.get(f"/products/{product_id}", name="/products/[id]-cached")
    
    @task(5)
    def repeat_list_lookup(self):
        """Repeatedly fetch same list to test pagination cache."""
        self.client.get("/products?skip=0&limit=20", name="/products-cached")

# Load test configurations for Makefile
LOAD_TEST_CONFIGS = {
    "light": "--users=100 --spawn-rate=10",
    "moderate": "--users=500 --spawn-rate=25",
    "heavy": "--users=1000 --spawn-rate=50",
    "stress": "--users=5000 --spawn-rate=100",
}

if __name__ == "__main__":
    # Run with: locust -f tests/load_test.py --users=1000 --spawn-rate=50 -H http://localhost:8000
    print("Ethera Load Testing")
    print("==================")
    print("\nQuick commands:")
    for name, args in LOAD_TEST_CONFIGS.items():
        print(f"  {name:10s}: locust -f tests/load_test.py {args} -H http://localhost:8000")
