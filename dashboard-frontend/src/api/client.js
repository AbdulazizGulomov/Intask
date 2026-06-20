// src/api/client.js
import axios from "axios";

// All API requests go through this base URL.
// In dev, Vite proxies /api/* to Django at http://127.0.0.1:8000
// In prod, the React build is served by Nginx alongside Django, so /api/* resolves naturally.
const BASE_URL = "/api/dashboard";

// JWT storage keys (kept simple — using localStorage for now)
const ACCESS_KEY = "intask_access";
const REFRESH_KEY = "intask_refresh";

export const tokenStorage = {
  getAccess: () => localStorage.getItem(ACCESS_KEY),
  getRefresh: () => localStorage.getItem(REFRESH_KEY),
  set: ({ access, refresh }) => {
    if (access) localStorage.setItem(ACCESS_KEY, access);
    if (refresh) localStorage.setItem(REFRESH_KEY, refresh);
  },
  clear: () => {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
  },
};

// Main axios instance
const apiClient = axios.create({
  baseURL: BASE_URL,
  timeout: 15000,
  headers: { "Content-Type": "application/json" },
});

// Request interceptor: attach JWT to every request
apiClient.interceptors.request.use(
  (config) => {
    const access = tokenStorage.getAccess();
    if (access) {
      config.headers.Authorization = `Bearer ${access}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor: auto-refresh expired tokens (one retry per request)
let isRefreshing = false;
let pendingQueue = [];

const processQueue = (error, newAccess = null) => {
  pendingQueue.forEach(({ resolve, reject }) => {
    if (error) reject(error);
    else resolve(newAccess);
  });
  pendingQueue = [];
};

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // Only auto-refresh on 401, only once per request
    if (error.response?.status !== 401 || originalRequest._retry) {
      return Promise.reject(error);
    }

    // Don't try to refresh on the refresh endpoint itself (avoid infinite loop)
    if (originalRequest.url?.includes("/auth/refresh")) {
      tokenStorage.clear();
      return Promise.reject(error);
    }

    if (isRefreshing) {
      // Queue this request until the in-flight refresh finishes
      return new Promise((resolve, reject) => {
        pendingQueue.push({ resolve, reject });
      })
        .then((newAccess) => {
          originalRequest.headers.Authorization = `Bearer ${newAccess}`;
          return apiClient(originalRequest);
        })
        .catch((err) => Promise.reject(err));
    }

    originalRequest._retry = true;
    isRefreshing = true;

    try {
      const refresh = tokenStorage.getRefresh();
      if (!refresh) {
        tokenStorage.clear();
        return Promise.reject(error);
      }

      const { data } = await axios.post(`${BASE_URL}/auth/refresh/`, { refresh });
      const newAccess = data.access;
      const newRefresh = data.refresh || refresh;

      tokenStorage.set({ access: newAccess, refresh: newRefresh });

      apiClient.defaults.headers.common.Authorization = `Bearer ${newAccess}`;
      originalRequest.headers.Authorization = `Bearer ${newAccess}`;

      processQueue(null, newAccess);
      return apiClient(originalRequest);
    } catch (refreshError) {
      processQueue(refreshError, null);
      tokenStorage.clear();
      // Trigger redirect to /login by reloading; AuthContext will catch it
      if (typeof window !== "undefined") {
        window.location.href = "/dashboard/login";
      }
      return Promise.reject(refreshError);
    } finally {
      isRefreshing = false;
    }
  }
);

export default apiClient;