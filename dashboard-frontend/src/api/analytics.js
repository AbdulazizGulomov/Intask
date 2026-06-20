// src/api/analytics.js
// Analytics endpoints. Reuses the dashboard apiClient (JWT + /api/dashboard base),
// so paths are relative to /api/dashboard/.
import apiClient from "./client";

// All analytics queries share the same date-range + district params.
function params({ from, to, district } = {}) {
  const p = {};
  if (from) p.from = from;
  if (to) p.to = to;
  if (district) p.district = district;
  return { params: p };
}

export async function fetchAnalyticsKpis(filters) {
  const { data } = await apiClient.get("/analytics/kpis/", params(filters));
  return data;
}

export async function fetchAnalyticsFunnel(filters) {
  const { data } = await apiClient.get("/analytics/funnel/", params(filters));
  return data;
}

export async function fetchAnalyticsClientsTrend(filters) {
  const { data } = await apiClient.get("/analytics/clients-trend/", params(filters));
  return data;
}

export async function fetchAnalyticsSupplyDemand(filters) {
  const { data } = await apiClient.get("/analytics/supply-demand/", params(filters));
  return data;
}
