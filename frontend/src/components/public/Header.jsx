import { useState } from "react";
import { Link, NavLink, useNavigate } from "react-router-dom";
import { Search, Menu, Facebook, Instagram, Youtube } from "lucide-react";
import { useSite } from "../../lib/auth";
import { fmtDate, WEEKDAYS } from "../../lib/api";
import { Sheet, SheetContent, SheetTitle, SheetTrigger } from "../ui/sheet";
import { useWeather, wx } from "./WeatherWidget";
import { AdSlot } from "./AdSlot";

function SearchBox({ onDone, id }) {
  const [q, setQ] = useState("");
  const nav = useNavigate();
  const submit = (e) => {
    e.preventDefault();
    if (q.trim()) { nav(`/pretraga?q=${encodeURIComponent(q.trim())}`); onDone?.(); }
  };
  return (
    <form onSubmit={submit} role="search" className="relative w-full">
      <label htmlFor={id} className="sr-only">Pretraga vijesti</label>
      <input id={id} value={q} onChange={(e) => setQ(e.target.value)} placeholder="Pretraži vijesti…" data-testid={`${id}-input`}
        className="w-full bg-white/10 border border-white/20 text-white placeholder-white/50 rounded-full pl-4 pr-10 py-2 text-sm focus:bg-white focus:text-ccn-navy focus:placeholder-slate-400 transition-colors" />
      <button type="submit" aria-label="Traži" className="absolute right-3 top-1/2 -translate-y-1/2 text-ccn-teal" data-testid={`${id}-submit`}><Search className="w-4 h-4" /></button>
    </form>
  );
}

function TopBar({ site }) {
  const w = useWeather();
  const today = `${WEEKDAYS[new Date().getDay()]}, ${fmtDate(new Date().toISOString(), false)}`;
  const s = site.social || {};
  return (
    <div className="bg-[#071426] text-white/70 text-xs">
      <div className="max-w-7xl mx-auto px-4 h-8 flex items-center justify-between">
        <span className="capitalize" data-testid="topbar-date">{today}</span>
        <div className="flex items-center gap-4">
          {w?.current && <span className="hidden sm:inline">Cazin {Math.round(w.current.temperature_2m)}°C · {wx(w.current.weather_code)[2]}</span>}
          <Link to="/kamere" className="hidden sm:inline hover:text-ccn-teal">Kamere granica</Link>
          {s.facebook && <a href={s.facebook} aria-label="Facebook" target="_blank" rel="noopener noreferrer"><Facebook className="w-3.5 h-3.5" /></a>}
          {s.instagram && <a href={s.instagram} aria-label="Instagram" target="_blank" rel="noopener noreferrer"><Instagram className="w-3.5 h-3.5" /></a>}
          {s.youtube && <a href={s.youtube} aria-label="YouTube" target="_blank" rel="noopener noreferrer"><Youtube className="w-3.5 h-3.5" /></a>}
        </div>
      </div>
    </div>
  );
}

export function Header() {
  const { site } = useSite();
  const [open, setOpen] = useState(false);
  const menu = site.main_menu || [{ label: "Naslovna", url: "/" }];
  return (
    <header className="sticky top-0 z-40 shadow-md">
      <a href="#main" className="skip-link">Preskoči na sadržaj</a>
      <TopBar site={site} />
      <div className="bg-ccn-navy">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center gap-4">
          <Sheet open={open} onOpenChange={setOpen}>
            <SheetTrigger asChild>
              <button className="lg:hidden text-white" aria-label="Meni" data-testid="mobile-menu-button"><Menu className="w-6 h-6" /></button>
            </SheetTrigger>
            <SheetContent side="left" className="bg-ccn-navy text-white border-ccn-navy2 w-[300px]">
              <SheetTitle className="sr-only">Navigacija</SheetTitle>
              <img src="/logo-web.webp" alt={site.site_name} className="h-16 w-auto mb-6" />
              <SearchBox id="mobile-search" onDone={() => setOpen(false)} />
              <nav className="mt-6 flex flex-col" data-testid="mobile-nav">
                {menu.map((m) => (
                  <Link key={m.url} to={m.url} onClick={() => setOpen(false)} className="py-3 border-b border-white/10 font-semibold hover:text-ccn-teal">{m.label}</Link>
                ))}
                <Link to="/prijavite-vijest" onClick={() => setOpen(false)} className="py-3 text-ccn-gold font-semibold">Prijavite vijest</Link>
              </nav>
            </SheetContent>
          </Sheet>
          <Link to="/" className="shrink-0" data-testid="header-logo">
            <img src={site.logo_url || "/logo-web.webp"} alt={site.site_name} className="h-12 md:h-16 w-auto" width="192" height="64" />
          </Link>
          <div className="flex-1" />
          <div className="hidden md:block w-72"><SearchBox id="header-search" /></div>
          <Link to="/prijavite-vijest" className="hidden lg:inline-flex bg-ccn-gold text-ccn-navy font-bold text-sm px-4 py-2 rounded-full hover:bg-white transition-colors" data-testid="header-submit-news">Prijavite vijest</Link>
          <Link to="/pretraga" className="md:hidden text-white" aria-label="Pretraga" data-testid="mobile-search-link"><Search className="w-5 h-5" /></Link>
        </div>
        <nav className="hidden lg:block border-t border-white/10" aria-label="Glavni meni">
          <div className="max-w-7xl mx-auto px-4 flex gap-1 overflow-x-auto">
            {menu.map((m) => (
              <NavLink key={m.url} to={m.url} end={m.url === "/"} data-testid={`nav-${m.url.replace(/\W+/g, "-")}`}
                className={({ isActive }) => `px-3 py-2.5 text-sm font-semibold whitespace-nowrap border-b-2 transition-colors ${isActive ? "text-ccn-teal border-ccn-teal" : "text-white/85 border-transparent hover:text-ccn-teal"}`}>
                {m.label}
              </NavLink>
            ))}
          </div>
        </nav>
      </div>
    </header>
  );
}

export function HeaderAds() {
  return (
    <div className="max-w-7xl mx-auto px-4">
      <AdSlot position="header_banner" className="pt-4 hidden md:block" />
      <AdSlot position="mobile_banner" className="pt-3 md:hidden" />
      <AdSlot position="below_nav" className="pt-3" />
    </div>
  );
}
