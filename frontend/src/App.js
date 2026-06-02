import { useEffect, useState } from "react";
import {
  getProducts,
  createProduct,
  updateProduct,
  deleteProduct,
  getCustomers,
  createCustomer,
  deleteCustomer,
  getOrders,
  createOrder,
  deleteOrder,
} from "./api";

const tabs = ["Dashboard", "Products", "Customers", "Orders"];

function App() {
  const [activeTab, setActiveTab] = useState("Dashboard");
  const [products, setProducts] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [orders, setOrders] = useState([]);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [productForm, setProductForm] = useState({ name: "", sku: "", price: "", quantity: "" });
  const [customerForm, setCustomerForm] = useState({ full_name: "", email: "", phone: "" });
  const [orderForm, setOrderForm] = useState({ customer_id: "", items: [{ product_id: "", quantity: "" }] });
  const [selectedOrder, setSelectedOrder] = useState(null);
  const [editId, setEditId] = useState(null);

  useEffect(() => {
    loadAll();
  }, []);

  const loadAll = async () => {
    try {
      const [prod, cust, ord] = await Promise.all([getProducts(), getCustomers(), getOrders()]);
      setProducts(prod);
      setCustomers(cust);
      setOrders(ord);
    } catch (err) {
      setError(err.message);
    }
  };

  const handleSubmitProduct = async (e) => {
    e.preventDefault();
    clearMessages();
    try {
      if (editId) {
        await updateProduct(editId, {
          ...productForm,
          price: Number(productForm.price),
          quantity: Number(productForm.quantity),
        });
        setMessage("Product updated.");
      } else {
        await createProduct({
          ...productForm,
          price: Number(productForm.price),
          quantity: Number(productForm.quantity),
        });
        setMessage("Product created.");
      }
      setProductForm({ name: "", sku: "", price: "", quantity: "" });
      setEditId(null);
      loadAll();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleProductEdit = (product) => {
    setEditId(product.id);
    setProductForm({ name: product.name, sku: product.sku, price: product.price, quantity: product.quantity });
    setActiveTab("Products");
    clearMessages();
  };

  const handleDeleteProduct = async (id) => {
    clearMessages();
    try {
      await deleteProduct(id);
      setMessage("Product deleted.");
      loadAll();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleSubmitCustomer = async (e) => {
    e.preventDefault();
    clearMessages();
    try {
      await createCustomer(customerForm);
      setMessage("Customer created.");
      setCustomerForm({ full_name: "", email: "", phone: "" });
      loadAll();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleDeleteCustomer = async (id) => {
    clearMessages();
    try {
      await deleteCustomer(id);
      setMessage("Customer deleted.");
      loadAll();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleOrderItemChange = (index, field, value) => {
    const items = [...orderForm.items];
    items[index][field] = value;
    setOrderForm({ ...orderForm, items });
  };

  const addOrderItem = () => {
    setOrderForm({ ...orderForm, items: [...orderForm.items, { product_id: "", quantity: "" }] });
  };

  const handleSubmitOrder = async (e) => {
    e.preventDefault();
    clearMessages();
    try {
      await createOrder({
        customer_id: Number(orderForm.customer_id),
        items: orderForm.items.map((item) => ({ product_id: Number(item.product_id), quantity: Number(item.quantity) })),
      });
      setMessage("Order created.");
      setOrderForm({ customer_id: "", items: [{ product_id: "", quantity: "" }] });
      loadAll();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleViewOrder = (order) => {
    setSelectedOrder(order);
    clearMessages();
  };

  const handleDeleteOrder = async (id) => {
    clearMessages();
    try {
      await deleteOrder(id);
      setMessage("Order cancelled.");
      if (selectedOrder?.id === id) {
        setSelectedOrder(null);
      }
      loadAll();
    } catch (err) {
      setError(err.message);
    }
  };

  const clearMessages = () => {
    setError("");
    setMessage("");
  };

  const lowStock = products.filter((p) => p.quantity <= 5);

  return (
    <div className="page">
      <header>
        <h1>Ethera Inventory Management</h1>
        <p>Inventory, customers, orders in one place.</p>
      </header>
      <nav>
        {tabs.map((tab) => (
          <button key={tab} className={activeTab === tab ? "active" : ""} onClick={() => { setActiveTab(tab); clearMessages(); }}>
            {tab}
          </button>
        ))}
      </nav>
      <main>
        {(error || message) && (
          <div className={`message ${error ? "error" : "success"}`}>{error || message}</div>
        )}
        {activeTab === "Dashboard" && (
          <section className="dashboard">
            <div className="card"><strong>Total Products</strong><span>{products.length}</span></div>
            <div className="card"><strong>Total Customers</strong><span>{customers.length}</span></div>
            <div className="card"><strong>Total Orders</strong><span>{orders.length}</span></div>
            <div className="card low-stock"><strong>Low Stock</strong><span>{lowStock.length}</span></div>
            <div className="wide">
              <h2>Low stock products</h2>
              <ul>
                {lowStock.length ? lowStock.map((p) => <li key={p.id}>{p.name} ({p.quantity})</li>) : <li>All stocks are healthy.</li>}
              </ul>
            </div>
          </section>
        )}

        {activeTab === "Products" && (
          <section>
            <h2>Manage products</h2>
            <form className="grid-form" onSubmit={handleSubmitProduct}>
              <input value={productForm.name} onChange={(e) => setProductForm({ ...productForm, name: e.target.value })} placeholder="Name" required />
              <input value={productForm.sku} onChange={(e) => setProductForm({ ...productForm, sku: e.target.value })} placeholder="SKU" required />
              <input value={productForm.price} onChange={(e) => setProductForm({ ...productForm, price: e.target.value })} placeholder="Price" type="number" step="0.01" required />
              <input value={productForm.quantity} onChange={(e) => setProductForm({ ...productForm, quantity: e.target.value })} placeholder="Quantity" type="number" required />
              <button type="submit">{editId ? "Update" : "Add"} Product</button>
            </form>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr><th>Name</th><th>SKU</th><th>Price</th><th>Stock</th><th>Actions</th></tr>
                </thead>
                <tbody>
                  {products.map((product) => (
                    <tr key={product.id}>
                      <td>{product.name}</td>
                      <td>{product.sku}</td>
                      <td>${product.price.toFixed(2)}</td>
                      <td>{product.quantity}</td>
                      <td>
                        <button onClick={() => handleProductEdit(product)}>Edit</button>
                        <button className="danger" onClick={() => handleDeleteProduct(product.id)}>Delete</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}

        {activeTab === "Customers" && (
          <section>
            <h2>Manage customers</h2>
            <form className="grid-form" onSubmit={handleSubmitCustomer}>
              <input value={customerForm.full_name} onChange={(e) => setCustomerForm({ ...customerForm, full_name: e.target.value })} placeholder="Full name" required />
              <input value={customerForm.email} onChange={(e) => setCustomerForm({ ...customerForm, email: e.target.value })} placeholder="Email" type="email" required />
              <input value={customerForm.phone} onChange={(e) => setCustomerForm({ ...customerForm, phone: e.target.value })} placeholder="Phone" required />
              <button type="submit">Add Customer</button>
            </form>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr><th>Name</th><th>Email</th><th>Phone</th><th>Action</th></tr>
                </thead>
                <tbody>
                  {customers.map((customer) => (
                    <tr key={customer.id}>
                      <td>{customer.full_name}</td>
                      <td>{customer.email}</td>
                      <td>{customer.phone}</td>
                      <td><button className="danger" onClick={() => handleDeleteCustomer(customer.id)}>Delete</button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}

        {activeTab === "Orders" && (
          <section>
            <h2>Orders</h2>
            <form className="order-form" onSubmit={handleSubmitOrder}>
              <select value={orderForm.customer_id} onChange={(e) => setOrderForm({ ...orderForm, customer_id: e.target.value })} required>
                <option value="">Select customer</option>
                {customers.map((cust) => <option key={cust.id} value={cust.id}>{cust.full_name}</option>)}
              </select>
              {orderForm.items.map((item, index) => (
                <div key={index} className="item-row">
                  <select value={item.product_id} onChange={(e) => handleOrderItemChange(index, "product_id", e.target.value)} required>
                    <option value="">Select product</option>
                    {products.map((prod) => <option key={prod.id} value={prod.id}>{prod.name} ({prod.quantity} left)</option>)}
                  </select>
                  <input value={item.quantity} onChange={(e) => handleOrderItemChange(index, "quantity", e.target.value)} type="number" min="1" placeholder="Qty" required />
                </div>
              ))}
              <button type="button" onClick={addOrderItem}>Add item</button>
              <button type="submit">Create order</button>
            </form>
            {selectedOrder && (
              <div className="details-card">
                <h3>Order #{selectedOrder.id} details</h3>
                <p><strong>Customer:</strong> {customers.find((c) => c.id === selectedOrder.customer_id)?.full_name || "Unknown"}</p>
                <p><strong>Total:</strong> ${selectedOrder.total_amount.toFixed(2)}</p>
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr><th>Product</th><th>Qty</th><th>Price</th><th>Subtotal</th></tr>
                    </thead>
                    <tbody>
                      {selectedOrder.items.map((item, idx) => (
                        <tr key={idx}>
                          <td>{item.product_name}</td>
                          <td>{item.quantity}</td>
                          <td>${item.price.toFixed(2)}</td>
                          <td>${(item.price * item.quantity).toFixed(2)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
            <div className="table-wrap">
              <table>
                <thead>
                  <tr><th>ID</th><th>Customer</th><th>Total</th><th>Items</th><th>Action</th></tr>
                </thead>
                <tbody>
                  {orders.map((order) => (
                    <tr key={order.id}>
                      <td>{order.id}</td>
                      <td>{customers.find((c) => c.id === order.customer_id)?.full_name || "Unknown"}</td>
                      <td>${order.total_amount.toFixed(2)}</td>
                      <td>{order.items.map((item) => `${item.product_name} x${item.quantity}`).join(", ")}</td>
                      <td>
                        <button onClick={() => handleViewOrder(order)}>View</button>
                        <button className="danger" onClick={() => handleDeleteOrder(order.id)}>Cancel</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}
      </main>
    </div>
  );
}

export default App;
