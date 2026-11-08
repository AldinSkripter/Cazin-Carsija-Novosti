import { useEffect } from "react";
import { api } from "./api";

function setMeta(attr, key, content) {
  let el = document.head.querySelector(`meta[${attr}="${key}"]`);
  if (!el) {
    el = document.createElement("meta");
    el.setAttribute(attr, key);
    document.head.appendChild(el);
  }
  el.setAttribute("content", content || "");
}

export function useSeo({ title, description, image, type = "website", canonical, jsonLd, noindex, siteName = "Cazin Čaršija Novosti" }) {
  useEffect(() => {
    const full = title ? `${title} | ${siteName}` : `${siteName} – Vijesti iz Cazina, Krajine, BiH i svijeta`;
    document.title = full;
    const url = canonical || window.location.origin + window.location.pathname;
    const img = image ? (image.startsWith("http") ? image : window.location.origin + image) : window.location.origin + "/og-image.jpg";
    setMeta("name", "description", description || "Najnovije vijesti iz Cazina, Unsko-sanskog kantona, Bosne i Hercegovine, regiona i svijeta.");
    setMeta("name", "robots", noindex ? "noindex, nofollow" : "index, follow, max-image-preview:large");
    setMeta("property", "og:title", title || siteName);
    setMeta("property", "og:description", description || "");
    setMeta("property", "og:image", img);
    setMeta("property", "og:type", type);
    setMeta("property", "og:url", url);
    setMeta("property", "og:site_name", siteName);
    setMeta("name", "twitter:card", "summary_large_image");
    setMeta("name", "twitter:title", title || siteName);
    setMeta("name", "twitter:description", description || "");
    setMeta("name", "twitter:image", img);
    let link = document.head.querySelector('link[rel="canonical"]');
    if (!link) {
      link = document.createElement("link");
      link.rel = "canonical";
      document.head.appendChild(link);
    }
    link.href = url;
    let ld = document.getElementById("ld-json");
    if (jsonLd) {
      if (!ld) {
        ld = document.createElement("script");
        ld.type = "application/ld+json";
        ld.id = "ld-json";
        document.head.appendChild(ld);
      }
      ld.textContent = JSON.stringify(jsonLd);
    } else if (ld) {
      ld.remove();
    }
  }, [title, description, image, type, canonical, jsonLd, noindex, siteName]);
}

const rid = () => Math.random().toString(36).slice(2) + Date.now().toString(36);

export function trackView(articleId) {
  let sid = sessionStorage.getItem("ccn_sid");
  if (!sid) { sid = rid(); sessionStorage.setItem("ccn_sid", sid); }
  let vid = localStorage.getItem("ccn_vid");
  if (!vid) { vid = rid(); localStorage.setItem("ccn_vid", vid); }
  api.post("/public/track", {
    path: window.location.pathname, article_id: articleId, session_id: sid, visitor_id: vid,
    referrer: document.referrer, mobile: window.innerWidth < 768,
  }).catch(() => {});
}

export function loadAnalytics(site) {
  const consent = JSON.parse(localStorage.getItem("ccn_consent") || "null");
  if (!consent?.analytics || window.__ga_loaded) return;
  if (site.ga4_id && /^G-[A-Z0-9]+$/.test(site.ga4_id)) {
    window.__ga_loaded = true;
    const s = document.createElement("script");
    s.async = true;
    s.src = `https://www.googletagmanager.com/gtag/js?id=${site.ga4_id}`;
    document.head.appendChild(s);
    window.dataLayer = window.dataLayer || [];
    window.gtag = function () { window.dataLayer.push(arguments); };
    window.gtag("js", new Date());
    window.gtag("config", site.ga4_id, { anonymize_ip: true });
  }
  if (site.plausible_domain) {
    const p = document.createElement("script");
    p.defer = true;
    p.dataset.domain = site.plausible_domain;
    p.src = "https://plausible.io/js/script.js";
    document.head.appendChild(p);
  }
}
