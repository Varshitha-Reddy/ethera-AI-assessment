const DEFAULT_API_URL =
  typeof window !== "undefined"
    ? `${window.location.protocol}//${window.location.hostname}:8000`
    : "http://localhost:8000";
const API_URL = process.env.REACT_APP_API_URL || DEFAULT_API_URL;

export async function fetchJson(path, options = {}) {
  const response = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(body?.detail || body?.message || "Request failed");
  }
  return body;
}

export const getProducts = () => fetchJson("/products");
export const createProduct = (payload) => fetchJson("/products", { method: "POST", body: JSON.stringify(payload) });
export const updateProduct = (id, payload) => fetchJson(`/products/${id}`, { method: "PUT", body: JSON.stringify(payload) });
export const deleteProduct = (id) => fetchJson(`/products/${id}`, { method: "DELETE" });
export const getCustomers = () => fetchJson("/customers");
export const createCustomer = (payload) => fetchJson("/customers", { method: "POST", body: JSON.stringify(payload) });
export const deleteCustomer = (id) => fetchJson(`/customers/${id}`, { method: "DELETE" });
export const getOrders = () => fetchJson("/orders");
export const getOrder = (id) => fetchJson(`/orders/${id}`);
export const createOrder = (payload) => fetchJson("/orders", { method: "POST", body: JSON.stringify(payload) });
export const deleteOrder = (id) => fetchJson(`/orders/${id}`, { method: "DELETE" });
