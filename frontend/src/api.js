const DEFAULT_API_URL =
  typeof window !== "undefined"
    ? `${window.location.protocol}//${window.location.hostname}:8000`
    : "http://localhost:8000";
const API_URL = process.env.REACT_APP_API_URL || DEFAULT_API_URL;

export async function fetchJson(path, options = {}) {
  const token = typeof window !== "undefined" ? localStorage.getItem("ethera_token") : null;
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers || {}),
    },
  });
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(body?.detail || body?.message || "Request failed");
  }
  return body;
}

export async function login(username, password) {
  const response = await fetch(`${API_URL}/auth/token`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({ username, password }),
  });
  const body = await response.json().catch(() => null);
  if (!response.ok) throw new Error(body?.error || body?.detail || "Login failed");
  localStorage.setItem("ethera_token", body.access_token);
  return body;
}

export function logout() {
  localStorage.removeItem("ethera_token");
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
