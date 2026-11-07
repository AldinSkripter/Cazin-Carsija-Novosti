import { useEffect, useState } from "react";
import { Link, NavLink, useNavigate } from "react-router-dom";
import { Search, Menu, Facebook, Instagram, Youtube, PenLine, Video } from "lucide-react";
import { useSite } from "../../lib/auth";
import { fmtDate, WEEKDAYS } from "../../lib/api";
import { Sheet, SheetContent, SheetTitle, SheetTrigger } from "../ui/sheet";
import { useWeather, wx } from "./WeatherWidget";
import { AdSlot } from "./AdSlot";

function SearchBox({ onDone, id, dark = true }) {
  const [q, setQ] = useState("");
  const nav = useNavigate();
  const submit = (e) => {
    e.preventDefault();
    if (q.trim()) { nav(`/pretraga?q=${encodeURIComponent(q.trim())}`); onDone?.(); }
  };
  return (
    <form onSubmit={submit} role="search" className="relative w-full group">
      <label htmlFor={id} className="sr-only">Pretraga vijesti</label>
      <Search className={`absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 ${dark ? "text-white/50 group-focus-within:text-ccn-tealdark" : "text-slate-400"}`} />
      <input id={id} value={q} onChange={(e) => setQ(e.target.value)} placeholder="Pretraži vijesti, teme, mjesta…" data-testid={`${id}-input`}
        className={`w-full rounded-full pl-10 pr-20 py-2.5 text-sm transition-all ${dark ? "bg-white/[0.08] border border-white/15 text-white placeholder-white/45 focus:bg-white focus:text-ccn-navy focus:placeholder-slate-400" : "bg-ccn-mist/60 border border-transparent"}`} />
      <button type="submit" className="absolute right-1.5 top-1/2 -translate-y-1/2 bg-ccn-teal text-ccn-navy text-xs font-bold px-3 py-1.5 rounded-full hover:bg-ccn-gold transition-colors" data-testid={`${id}-submit`}>Traži</button>
    </form>
  );
}

function TopBar({ site }) {
  const w = useWeather();
  const d = new Date();
  const s = site.social || {};
  const socials = [["facebook", Facebook], ["instagram", Instagram], ["youtube", Youtube]].filter(([k]) => s[k]);
  return (
    <div className="bg-[#06111f] text-white/65 text-[12px]">
      <div className="max-w-7xl mx-auto px-4 h-9 flex items-center justify-between gap-4">
        <span className="capitalize truncate" data-testid="topbar-date">{WEEKDAYS[d.getDay()]}, {fmtDate(d.toISOString(), false)}</span>
        <div className="flex items-center gap-5">
          {w?.current && <span className="hidden sm:flex items-center gap-1.5"><span className="text-ccn-gold font-semibold">Cazin</span> {Math.round(w.current.temperature_2m)}°C · {wx(w.current.weather_code)[2]}</span>}
          <Link to="/kamere" className="flex items-center gap-1.5 hover:text-white transition-colors" data-testid="topbar-cameras">
            <span className="relative flex h-2 w-2"><span className="animate-ping absolute h-full w-full rounded-full bg-ccn-red opacity-75" /><span className="relative rounded-full h-2 w-2 bg-ccn-red" /></span>
            Granice uživo
          </Link>
          {socials.map(([k, I]) => <a key={k} href={s[k]} aria-label={k} target="_blank" rel="noopener noreferrer" className="hover:text-ccn-teal"><I className="w-3.5 h-3.5" /></a>)}
        </div>
      </div>
    </div>
  );
}

export function Header() {
  const { site } = useSite();
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  useEffect(() => {
    const on = () => setScrolled(window.scrollY > 120);
    window.addEventListener("scroll", on, { passive: true });
    return () => window.removeEventListener("scroll", on);
  }, []);
  const menu = site.main_menu || [{ label: "Naslovna", url: "/" }];
  return (
    <>
      <a href="#main" className="skip-link">Preskoči na sadržaj</a>
      <TopBar site={site} />
      <header className="sticky top-0 z-40 bg-ccn-navy shadow-[0_6px_24px_-12px_rgba(0,0,0,0.6)]">
        <div className={`max-w-7xl mx-auto px-4 flex items-center gap-5 transition-all duration-300 ${scrolled ? "py-1.5" : "py-3 md:py-4"}`}>
          <Sheet open={open} onOpenChange={setOpen}>
            <SheetTrigger asChild>
              <button className="lg:hidden text-white p-1 -ml-1" aria-label="Meni" data-testid="mobile-menu-button"><Menu className="w-6 h-6" /></button>
            </SheetTrigger>
            <SheetContent side="left" className="bg-ccn-navy text-white border-ccn-navy2 w-[310px] overflow-y-auto">
              <SheetTitle className="sr-only">Navigacija</SheetTitle>
              <img src="/logo-web.webp" alt={site.site_name} className="h-16 w-auto mb-6" />
              <SearchBox id="mobile-search" onDone={() => setOpen(false)} />
              <nav className="mt-6 flex flex-col" data-testid="mobile-nav">
                {menu.map((m) => (
                  <Link key={m.url} to={m.url} onClick={() => setOpen(false)} className="py-3 border-b border-white/10 font-semibold hover:text-ccn-teal hover:pl-1 transition-all">{m.label}</Link>
                ))}
                <Link to="/prijavite-vijest" onClick={() => setOpen(false)} className="mt-5 bg-ccn-gold text-ccn-navy text-center font-bold py-3 rounded-full">Prijavite vijest</Link>
              </nav>
            </SheetContent>
          </Sheet>
          <Link to="/" className="shrink-0" data-testid="header-logo">
            <img src={site.logo_url || "/logo-web.webp"} alt={site.site_name} width="216" height="72"
              className={`w-auto transition-all duration-300 ${scrolled ? "h-10 md:h-12" : "h-12 md:h-[72px]"}`} />
          </Link>
          {!scrolled && site.tagline && <p className="hidden xl:block text-white/45 text-[13px] italic font-serif-news max-w-[220px] leading-snug border-l border-white/15 pl-5">{site.tagline}</p>}
          <div className="flex-1" />
          <div className="hidden md:block w-[340px]"><SearchBox id="header-search" /></div>
          <Link to="/prijavite-vijest" className="hidden lg:inline-flex items-center gap-2 bg-ccn-gold text-ccn-navy font-bold text-sm px-5 py-2.5 rounded-full hover:bg-white hover:-translate-y-0.5 transition-all" data-testid="header-submit-news">
            <PenLine className="w-4 h-4" />Prijavite vijest
          </Link>
          <Link to="/pretraga" className="md:hidden text-white p-1" aria-label="Pretraga" data-testid="mobile-search-link"><Search className="w-5 h-5" /></Link>
        </div>
        <nav className="hidden lg:block border-t border-white/[0.08] bg-ccn-navy2/40" aria-label="Glavni meni">
          <div className="max-w-7xl mx-auto px-4 flex items-center">
            <div className="flex gap-0.5 overflow-x-auto flex-1">
              {menu.map((m) => (
                <NavLink key={m.url} to={m.url} end={m.url === "/"} data-testid={`nav-${m.url.replace(/\W+/g, "-")}`}
                  className={({ isActive }) => `relative px-3.5 py-3 text-[14px] font-semibold whitespace-nowrap transition-colors after:absolute after:left-3.5 after:right-3.5 after:bottom-0 after:h-[3px] after:rounded-t after:transition-transform after:origin-left ${isActive ? "text-white after:bg-ccn-gold after:scale-x-100" : "text-white/75 hover:text-white after:bg-ccn-teal after:scale-x-0 hover:after:scale-x-100"}`}>
                  {m.label}
                </NavLink>
              ))}
            </div>
            <Link to="/kamere" className="ml-3 flex items-center gap-1.5 text-[12px] font-bold uppercase tracking-wider bg-ccn-red/15 text-white border border-ccn-red/50 px-3 py-1.5 rounded-full hover:bg-ccn-red transition-colors" data-testid="nav-cameras-live">
              <Video className="w-3.5 h-3.5" />Kamere uživo
            </Link>
          </div>
        </nav>
      </header>
    </>
  );
}

export function HeaderAds() {
  return (
    <div className="max-w-7xl mx-auto px-4">
      <AdSlot position="header_banner" className="pt-5 hidden md:block" />
      <AdSlot position="mobile_banner" className="pt-3 md:hidden" />
      <AdSlot position="below_nav" className="pt-3" />
    </div>
  );
}
