import axios from "axios";

export const BACKEND = process.env.REACT_APP_BACKEND_URL;
export const api = axios.create({ baseURL: `${BACKEND}/api`, withCredentials: true });

let refreshing = null;
api.interceptors.response.use(
  (r) => r,
  async (err) => {
    const cfg = err.config || {};
    const url = cfg.url || "";
    if (err.response?.status === 401 && !cfg._retry && !url.startsWith("/auth/")) {
      cfg._retry = true;
      try {
        refreshing = refreshing || api.post("/auth/refresh");
        await refreshing;
        refreshing = null;
        return api(cfg);
      } catch (e) {
        refreshing = null;
      }
    }
    return Promise.reject(err);
  }
);

export function errMsg(e) {
  const d = e?.response?.data?.detail;
  if (!d) return e?.message || "Došlo je do greške. Pokušajte ponovo.";
  if (typeof d === "string") return d;
  if (Array.isArray(d)) return d.map((x) => x?.msg || JSON.stringify(x)).join(" ");
  return d.msg || String(d);
}

export const mediaUrl = (u) => (u && u.startsWith("/api/") ? `${BACKEND}${u}` : u || "");
export const articleUrl = (a) => `/vijesti/${a.slug}`;
export const shareUrl = (a) => `${BACKEND}/api/share/${a.slug}`;

const MONTHS = ["januara", "februara", "marta", "aprila", "maja", "juna", "jula", "augusta", "septembra", "oktobra", "novembra", "decembra"];
export const WEEKDAYS = ["nedjelja", "ponedjeljak", "utorak", "srijeda", "četvrtak", "petak", "subota"];
const pad = (n) => String(n).padStart(2, "0");

export function fmtDate(iso, withTime = true) {
  if (!iso) return "";
  const d = new Date(iso);
  const base = `${d.getDate()}. ${MONTHS[d.getMonth()]} ${d.getFullYear()}.`;
  return withTime ? `${base} u ${pad(d.getHours())}:${pad(d.getMinutes())}` : base;
}

export function timeAgo(iso) {
  if (!iso) return "";
  const m = Math.floor((Date.now() - new Date(iso).getTime()) / 60000);
  if (m < 1) return "upravo";
  if (m < 60) return `prije ${m} min`;
  const h = Math.floor(m / 60);
  if (h < 24) return `prije ${h} h`;
  return fmtDate(iso, false);
}

export const STATUS_LABELS = {
  draft: "Nacrt", review: "Na pregledu", approved: "Odobreno", scheduled: "Zakazano",
  published: "Objavljeno", archived: "Arhivirano", rejected: "Odbijeno",
};
export const STATUS_COLORS = {
  draft: "bg-slate-200 text-slate-700", review: "bg-amber-100 text-amber-800", approved: "bg-teal-100 text-teal-800",
  scheduled: "bg-blue-100 text-blue-800", published: "bg-emerald-100 text-emerald-800", archived: "bg-zinc-200 text-zinc-600",
  rejected: "bg-red-100 text-red-700",
};
export const AD_POSITIONS = {
  header_banner: "Header banner", below_nav: "Ispod navigacije", home_top: "Početna – vrh", between_cards: "Između kartica vijesti",
  sidebar: "Sidebar", in_article: "Unutar članka", below_article: "Ispod članka", mobile_banner: "Mobilni banner", footer: "Footer",
  sponsored: "Sponzorisana pozicija",
};
