// src/api/reports.js
// Abuse-report moderation queue (App Store Guideline 1.2).
// Reuses the dashboard apiClient (JWT + /api/dashboard base), so paths here
// are relative to /api/dashboard/.
import apiClient from "./client";

export async function fetchReports({ page = 1, status = "", search = "" } = {}) {
  const params = { page };
  if (status) params.status = status;
  if (search) params.search = search;
  const { data } = await apiClient.get("/reports/", { params });
  return data; // { count, next, previous, results: [...] }
}

// The four moderation actions. Each returns the updated report, so the caller
// can drop it straight back into the list without a refetch.
export async function resolveReport(id) {
  const { data } = await apiClient.post(`/reports/${id}/resolve/`);
  return data;
}

export async function rejectReport(id) {
  const { data } = await apiClient.post(`/reports/${id}/reject/`);
  return data;
}

export async function hideReportedJob(id) {
  const { data } = await apiClient.post(`/reports/${id}/hide-job/`);
  return data;
}

export async function deactivateReportedUser(id) {
  const { data } = await apiClient.post(`/reports/${id}/deactivate-user/`);
  return data;
}
