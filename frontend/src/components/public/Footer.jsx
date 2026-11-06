import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../lib/api";
import { useSite } from "../../lib/auth";
import { loadAnalytics } from "../../lib/seo";
import { AdSlot } from "./AdSlot";

export function Footer() {
  const { site, cats } = useSite();
  const year = new Date().getFullYear();
  return (
    <footer className="bg-ccn-navy text-white/75 mt-16" data-testid="site-footer">
      <div className="max-w-7xl mx-auto px-4"><AdSlot position="footer" className="pt-8" /></div>
      <div className="max-w-7xl mx-auto px-4 py-12 grid gap-10 md:grid-cols-4">
        <div className="md:col-span-1">
          <img src={site.logo_url || "/logo-web.webp"} alt={site.site_name} className="h-20 w-auto" loading="lazy" />
          <p className="mt-4 text-sm">{site.tagline}</p>
          <p className="mt-4 text-sm">{site.address}<br />{site.contact_email}<br />{site.phone}</p>
        </div>
        <div>
          <h2 className="text-ccn-gold font-bold text-sm uppercase tracking-widest mb-4">Rubrike</h2>
          <ul className="grid grid-cols-2 gap-y-2 text-sm">
            {cats.filter((c) => !c.parent_id).slice(0, 16).map((c) => (
              <li key={c.id}><Link to={`/kategorija/${c.slug}`} className="hover:text-ccn-teal">{c.name}</Link></li>
            ))}
          </ul>
        </div>
        <div>
          <h2 className="text-ccn-gold font-bold text-sm uppercase tracking-widest mb-4">Portal</h2>
          <ul className="space-y-2 text-sm">
            {(site.footer_menu || []).map((m) => (
              <li key={m.url}>{m.url.startsWith("/api") ? <a href={`${process.env.REACT_APP_BACKEND_URL}${m.url}`} className="hover:text-ccn-teal">{m.label}</a> : <Link to={m.url} className="hover:text-ccn-teal">{m.label}</Link>}</li>
            ))}
          </ul>
        </div>
        <div>
          <h2 className="text-ccn-gold font-bold text-sm uppercase tracking-widest mb-4">Pratite nas</h2>
          <ul className="space-y-2 text-sm">
            {Object.entries(site.social || {}).filter(([, v]) => v).map(([k, v]) => (
              <li key={k}><a href={v} target="_blank" rel="noopener noreferrer" className="capitalize hover:text-ccn-teal">{k}</a></li>
            ))}
            <li><Link to="/kamere" className="hover:text-ccn-teal">Kamere uživo</Link></li>
            <li><button onClick={() => { localStorage.removeItem("ccn_consent"); window.location.reload(); }} className="hover:text-ccn-teal" data-testid="footer-cookie-settings">Postavke kolačića</button></li>
          </ul>
        </div>
      </div>
      <div className="border-t border-white/10 py-5 text-center text-xs text-white/50 px-4">
        © {year} {site.site_name}. {site.footer_text}
      </div>
    </footer>
  );
}

export function CookieBanner() {
  const { site } = useSite();
  const [show, setShow] = useState(false);
  useEffect(() => {
    if (!localStorage.getItem("ccn_consent")) setShow(true);
    else loadAnalytics(site);
  }, [site]);
  const save = (analytics, marketing) => {
    const c = { analytics, marketing, at: new Date().toISOString() };
    localStorage.setItem("ccn_consent", JSON.stringify(c));
    api.post("/public/consent", { ...c, visitor_id: localStorage.getItem("ccn_vid") }).catch(() => {});
    setShow(false);
    loadAnalytics(site);
  };
  if (!show) return null;
  return (
    <div className="fixed bottom-0 inset-x-0 z-50 p-4" data-testid="cookie-banner" role="dialog" aria-label="Kolačići">
      <div className="max-w-3xl mx-auto bg-white rounded-md shadow-2xl border border-ccn-mist p-5 md:flex items-center gap-5">
        <p className="text-sm text-slate-700 flex-1">
          Koristimo neophodne kolačiće za rad portala, a uz vaš pristanak i analitičke i marketinške kolačiće.{" "}
          <Link to="/stranica/politika-kolacica" className="text-ccn-tealdark underline">Politika kolačića</Link>
        </p>
        <div className="flex gap-2 mt-3 md:mt-0 shrink-0">
          <button onClick={() => save(false, false)} className="px-3 py-2 text-sm border border-slate-300 rounded-sm" data-testid="cookie-necessary">Samo neophodni</button>
          <button onClick={() => save(true, true)} className="px-3 py-2 text-sm bg-ccn-navy text-white rounded-sm font-semibold" data-testid="cookie-accept-all">Prihvati sve</button>
        </div>
      </div>
    </div>
  );
}
