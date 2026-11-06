import { createContext, useContext, useEffect, useState, useCallback } from "react";
import { api } from "./api";

const AuthCtx = createContext(null);
const SiteCtx = createContext({});

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const load = useCallback(async () => {
    try {
      const { data } = await api.get("/auth/me");
      setUser(data);
    } catch (e) {
      setUser(false);
    }
  }, []);
  useEffect(() => {
    if (window.location.pathname.startsWith("/admin")) {
      load();
    } else {
      setUser(undefined);
    }
  }, [load]);
  const can = (...perms) => !!user && perms.some((p) => user.permissions?.includes(p));
  const logout = async () => {
    try { await api.post("/auth/logout"); } catch (e) { /* ignore */ }
    setUser(false);
  };
  return <AuthCtx.Provider value={{ user, setUser, reload: load, can, logout }}>{children}</AuthCtx.Provider>;
}

export const useAuth = () => useContext(AuthCtx);

export function SiteProvider({ children }) {
  const [site, setSite] = useState({ site_name: "Cazin Čaršija Novosti" });
  const [cats, setCats] = useState([]);
  useEffect(() => {
    api.get("/public/settings").then((r) => setSite(r.data)).catch(() => {});
    api.get("/public/categories").then((r) => setCats(r.data)).catch(() => {});
  }, []);
  return <SiteCtx.Provider value={{ site, cats }}>{children}</SiteCtx.Provider>;
}

export const useSite = () => useContext(SiteCtx);
