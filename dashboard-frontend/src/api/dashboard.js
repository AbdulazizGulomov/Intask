// src/api/dashboard.js
import apiClient, { tokenStorage } from "./client";

// =====================================================
// AUTH
// =====================================================
export async function login(phone, password) {
  const { data } = await apiClient.post("/auth/login/", { phone, password });
  tokenStorage.set({ access: data.access, refresh: data.refresh });
  return data; // { access, refresh, user }
}

export async function logout() {
  const refresh = tokenStorage.getRefresh();
  try {
    if (refresh) {
      await apiClient.post("/auth/logout/", { refresh });
    }
  } catch (err) {
    // Ignore — we're logging out anyway
    console.warn("Logout request failed (ignored):", err.message);
  } finally {
    tokenStorage.clear();
  }
}

export async function fetchMe() {
  const { data } = await apiClient.get("/auth/me/");
  return data;
}

// =====================================================
// SETTINGS
// =====================================================
export async function fetchSettingsProfile() {
  const { data } = await apiClient.get("/settings/profile/");
  return data;
}

export async function updateSettingsProfile(payload) {
  // payload: { username }
  const { data } = await apiClient.patch("/settings/profile/", payload);
  return data;
}

export async function changePassword(payload) {
  // payload: { current_password, new_password, confirm }
  const { data } = await apiClient.post("/settings/password/", payload);
  return data;
}

// Operator management (admin-only)
export async function listOperators() {
  const { data } = await apiClient.get("/settings/operators/");
  return data;
}

export async function createOperator(payload) {
  // payload: { phone, username, password }
  const { data } = await apiClient.post("/settings/operators/", payload);
  return data;
}

export async function setOperatorActive(id, isActive) {
  const { data } = await apiClient.patch(`/settings/operators/${id}/`, {
    is_active: isActive,
  });
  return data;
}

// =====================================================
// STATS
// =====================================================
export async function fetchStats() {
  const { data } = await apiClient.get("/stats/");
  return data;
}

// =====================================================
// CHARTS
// =====================================================
export async function fetchOrdersTrendChart() {
  const { data } = await apiClient.get("/charts/orders-trend/");
  return data;
}

export async function fetchStatusMixChart() {
  const { data } = await apiClient.get("/charts/status-mix/");
  return data;
}

export async function fetchTopProfessionsChart() {
  const { data } = await apiClient.get("/charts/top-professions/");
  return data;
}

export async function fetchRevenueByDistrictChart() {
  const { data } = await apiClient.get("/charts/revenue-by-district/");
  return data;
}

// =====================================================
// ORDERS
// =====================================================
export async function fetchOrders(params = {}) {
  // params can include: page, search, status, ordering, from, to
  const { data } = await apiClient.get("/orders/", { params });
  return data; // { count, next, previous, results: [...] }
}

export async function fetchOrderDetail(id) {
  const { data } = await apiClient.get(`/orders/${id}/`);
  return data;
}

export async function updateOrder(id, payload) {
  const { data } = await apiClient.patch(`/orders/${id}/`, payload);
  return data;
}

// =====================================================
// MASTERS
// =====================================================
export async function fetchMasters(params = {}) {
  const { data } = await apiClient.get("/masters/", { params });
  return data;
}

export async function fetchMasterDetail(id) {
  const { data } = await apiClient.get(`/masters/${id}/`);
  return data;
}

// =====================================================
// CLIENTS
// =====================================================
export async function fetchClients(params = {}) {
  // params can include: page, search, ordering, is_active
  const { data } = await apiClient.get("/clients/", { params });
  return data; // { count, next, previous, results: [...] }
}

export async function fetchClientDetail(id) {
  const { data } = await apiClient.get(`/clients/${id}/`);
  return data;
}