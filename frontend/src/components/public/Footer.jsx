import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Mail, Phone, MapPin, Rss } from "lucide-react";
import { toast } from "sonner";
import { api, errMsg, BACKEND } from "../../lib/api";
import { useSite } from "../../lib/auth";
import { loadAnalytics } from "../../lib/seo";
import { AdSlot } from "./AdSlot";
import { AdsterraBanner } from "./AdsterraBanner";

function NewsletterBand() {
  const [email, setEmail] = useState("");
  const [consent, setConsent] = useState(false);
  const submit = async (e) => {
    e.preventDefault();
    try { const { data } = await api.post("/public/newsletter/subscribe", { email, consent, frequency: "daily" }); toast.success(data.message); setEmail(""); }
    catch (err) { toast.error(errMsg(err)); }
  };
  return (
    <div className="bg-ccn-teal">
      <form onSubmit={submit} className="max-w-7xl mx-auto px-4 py-8 grid md:grid-cols-12 gap-4 items-center" data-testid="footer-newsletter">
        <div className="md:col-span-5">
          <p className="font-serif-news text-2xl font-black text-ccn-navy">Vijesti iz Krajine, svako jutro.</p>
          <p className="text-ccn-navy/75 text-sm mt-1">Prijavite se na dnevni pregled najvažnijih vijesti.</p>
        </div>
        <div className="md:col-span-7">
          <div className="flex gap-2">
            <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="vas@email.com" aria-label="E-mail" data-testid="footer-newsletter-email"
              className="flex-1 rounded-full px-5 py-3 text-sm text-ccn-navy border-0 focus:ring-2 focus:ring-ccn-navy" />
            <button disabled={!consent} className="bg-ccn-navy text-white font-bold px-6 rounded-full hover:bg-ccn-navy2 disabled:opacity-60 transition-colors" data-testid="footer-newsletter-submit">Prijavi se</button>
          </div>
          <label className="flex gap-2 items-center mt-2 text-xs text-ccn-navy/80">
            <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} data-testid="footer-newsletter-consent" />Saglasan/na sam s primanjem newslettera i politikom privatnosti.
          </label>
        </div>
      </form>
    </div>
  );
}

const FLink = ({ m }) => (m.url.startsWith("/api")
  ? <a href={`${BACKEND}${m.url}`} className="hover:text-ccn-teal transition-colors">{m.label}</a>
  : <Link to={m.url} className="hover:text-ccn-teal transition-colors">{m.label}</Link>);

export function Footer() {
  const { site, cats } = useSite();
  const year = new Date().getFullYear();
  return (
    <footer className="mt-20" data-testid="site-footer">
      <div className="max-w-7xl mx-auto px-2 pb-8"><AdsterraBanner variant="rectangle" /></div>
      <div className="max-w-7xl mx-auto px-4"><AdSlot position="footer" className="pb-8" /></div>
      <NewsletterBand />
      <div className="bg-ccn-navy text-white/70 border-t-4 border-ccn-gold">
        <div className="max-w-7xl mx-auto px-4 py-14 grid gap-10 md:grid-cols-12">
          <div className="md:col-span-4">
            <img src={site.logo_url || "/logo-web.webp"} alt={site.site_name} className="h-20 w-auto" loading="lazy" />
            <p className="mt-5 text-sm leading-relaxed max-w-xs">{site.tagline}</p>
            <ul className="mt-5 space-y-2 text-sm">
              <li className="flex gap-2"><MapPin className="w-4 h-4 text-ccn-gold shrink-0 mt-0.5" />{site.address}</li>
              <li className="flex gap-2"><Mail className="w-4 h-4 text-ccn-gold shrink-0 mt-0.5" /><a href={`mailto:${site.contact_email}`} className="hover:text-ccn-teal transition-colors" data-testid="footer-email">{site.contact_email}</a></li>
              <li className="flex gap-2"><Phone className="w-4 h-4 text-ccn-gold shrink-0 mt-0.5" /><a href={`tel:${(site.phone || "").replace(/[^+\d]/g, "")}`} className="hover:text-ccn-teal transition-colors" data-testid="footer-phone">{site.phone}</a></li>
            </ul>
          </div>
          <div className="md:col-span-4">
            <h2 className="text-white font-bold text-xs uppercase tracking-[0.2em] mb-5">Rubrike</h2>
            <ul className="grid grid-cols-2 gap-y-2.5 text-sm">
              {cats.filter((c) => !c.parent_id).slice(0, 16).map((c) => <li key={c.id}><Link to={`/kategorija/${c.slug}`} className="hover:text-ccn-teal transition-colors">{c.name}</Link></li>)}
            </ul>
          </div>
          <div className="md:col-span-2">
            <h2 className="text-white font-bold text-xs uppercase tracking-[0.2em] mb-5">Portal</h2>
            <ul className="space-y-2.5 text-sm">{(site.footer_menu || []).map((m) => <li key={m.url}><FLink m={m} /></li>)}</ul>
          </div>
          <div className="md:col-span-2">
            <h2 className="text-white font-bold text-xs uppercase tracking-[0.2em] mb-5">Pratite nas</h2>
            <ul className="space-y-2.5 text-sm">
              {Object.entries(site.social || {}).filter(([, v]) => v).map(([k, v]) => <li key={k}><a href={v} target="_blank" rel="noopener noreferrer" className="capitalize hover:text-ccn-teal">{k}</a></li>)}
              <li><Link to="/kamere" className="hover:text-ccn-teal">Kamere uživo</Link></li>
              <li><a href={`${BACKEND}/api/rss.xml`} className="hover:text-ccn-teal flex items-center gap-1"><Rss className="w-3.5 h-3.5" />RSS</a></li>
              <li><button onClick={() => { localStorage.removeItem("ccn_consent"); window.location.reload(); }} className="hover:text-ccn-teal" data-testid="footer-cookie-settings">Postavke kolačića</button></li>
            </ul>
          </div>
        </div>
        <div className="border-t border-white/10">
          <div className="max-w-7xl mx-auto px-4 py-5 flex flex-col md:flex-row gap-2 justify-between text-xs text-white/45">
            <span>© {year} {site.site_name}. {site.footer_text}</span>
            <span className="font-serif-news italic text-ccn-gold/70">CČN · Cazin, Bosna i Hercegovina</span>
            <a href="https://jonuzovicdesign.de" target="_blank" rel="noopener" className="hover:text-ccn-teal transition-colors" data-testid="footer-designer-link">
              Izradio <span className="font-semibold text-white/80">JonuzovicDesign</span>
            </a>
          </div>
        </div>
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
    window.dispatchEvent(new Event("ccn-consent-change"));
    api.post("/public/consent", { ...c, visitor_id: localStorage.getItem("ccn_vid") }).catch(() => {});
    setShow(false);
    loadAnalytics(site);
  };
  if (!show) return null;
  return (
    <div className="fixed bottom-4 left-4 right-4 md:left-auto md:right-6 md:bottom-6 md:w-[420px] z-50 fade-up" data-testid="cookie-banner" role="dialog" aria-label="Kolačići">
      <div className="bg-ccn-navy text-white rounded-xl shadow-2xl p-5 border border-white/10">
        <p className="font-bold">Kolačići i privatnost</p>
        <p className="text-sm text-white/70 mt-1.5 leading-relaxed">
          Koristimo neophodne kolačiće za rad portala, a uz vaš pristanak i analitičke i marketinške.{" "}
          <Link to="/stranica/politika-kolacica" className="text-ccn-teal underline">Saznajte više</Link>
        </p>
        <div className="flex gap-2 mt-4">
          <button onClick={() => save(false, false)} className="flex-1 px-3 py-2.5 text-sm border border-white/25 rounded-full hover:bg-white/10 transition-colors" data-testid="cookie-necessary">Samo neophodni</button>
          <button onClick={() => save(true, true)} className="flex-1 px-3 py-2.5 text-sm bg-ccn-teal text-ccn-navy rounded-full font-bold hover:bg-ccn-gold transition-colors" data-testid="cookie-accept-all">Prihvati sve</button>
        </div>
      </div>
    </div>
  );
}
