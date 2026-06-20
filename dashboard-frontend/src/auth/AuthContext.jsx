// src/auth/AuthContext.jsx
import { createContext, useContext, useState, useEffect, useCallback } from "react";
import { fetchMe, login as apiLogin, logout as apiLogout } from "../api/dashboard";
import { tokenStorage } from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true); // true while we check existing token on mount

  // On mount: if there's a stored access token, try to fetch /me/ to verify it
  useEffect(() => {
    const access = tokenStorage.getAccess();
    if (!access) {
      setLoading(false);
      return;
    }
    fetchMe()
      .then((me) => {
        setUser(me);
      })
      .catch(() => {
        // Invalid/expired token — clear it
        tokenStorage.clear();
        setUser(null);
      })
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (phone, password) => {
    const data = await apiLogin(phone, password);
    setUser(data.user);
    return data.user;
  }, []);

  const logout = useCallback(async () => {
    await apiLogout();
    setUser(null);
  }, []);

  const value = {
    user,
    loading,
    login,
    logout,
    isAuthenticated: !!user,
    isOperator: user?.role === "operator",
    isAdmin: user?.role === "admin" || user?.is_superuser,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used inside <AuthProvider>");
  }
  return ctx;
}