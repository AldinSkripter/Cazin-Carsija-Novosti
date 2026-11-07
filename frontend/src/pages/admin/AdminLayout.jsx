import { useEffect, useState } from "react";
import { Link, NavLink, Navigate, Outlet, useNavigate } from "react-router-dom";
import {
  LayoutDashboard, FileText, FolderTree, Tags, Image, LayoutTemplate, Zap, Megaphone, MessageSquare, Inbox, Mail, Users,
  Video, ScrollText, Settings, BarChart3, FileCode, LogOut, Menu, Shield, ExternalLink, Plus,
} from "lucide-react";
import { useAuth } from "../../lib/auth";
import { Sheet, SheetContent, SheetTitle } from "../../components/ui/sheet";

export const NAV = [
  ["/admin", "Dashboard", LayoutDashboard, null],
  ["/admin/clanci", "Članci", FileText, ["articles.create", "articles.edit_own", "articles.edit_all"]],
  ["/admin/kategorije", "Kategorije", FolderTree, ["categories.manage"]],
  ["/admin/oznake", "Oznake", Tags, ["categories.manage"]],
  ["/admin/mediji", "Medijska biblioteka", Image, ["media.manage", "articles.create"]],
  ["/admin/pocetna", "Početna stranica", LayoutTemplate, ["homepage.manage"]],
  ["/admin/breaking", "Breaking News", Zap, ["breaking.manage"]],
  ["/admin/reklame", "Reklame", Megaphone, ["ads.manage"]],
  ["/admin/komentari", "Komentari", MessageSquare, ["comments.moderate"]],
  ["/admin/prijave", "Prijavljene vijesti", Inbox, ["submissions.manage"]],
  ["/admin/newsletter", "Newsletter", Mail, ["newsletter.manage"]],
  ["/admin/kamere", "Live kamere", Video, ["cameras.manage"]],
  ["/admin/stranice", "Stranice", FileCode, ["pages.manage"]],
  ["/admin/statistika", "Statistika", BarChart3, ["analytics.view"]],
  ["/admin/korisnici", "Korisnici i uloge", Users, ["users.manage"]],
  ["/admin/audit", "Audit log", ScrollText, ["audit.view"]],
  ["/admin/postavke", "Postavke", Settings, ["settings.manage"]],
];

const GROUPS = { "/admin/clanci": "Sadržaj", "/admin/pocetna": "Naslovna i marketing", "/admin/komentari": "Zajednica", "/admin/statistika": "Sistem" };

function SideNav({ onNav }) {
  const { can } = useAuth();
  return (
    <nav className="flex flex-col gap-0.5" data-testid="admin-sidebar">
      {NAV.filter(([, , , p]) => !p || can(...p)).map(([to, label, Icon]) => (
        <div key={to}>
          {GROUPS[to] && <p className="px-3 pt-5 pb-1.5 text-[10px] font-bold uppercase tracking-[0.2em] text-white/35">{GROUPS[to]}</p>}
          <NavLink to={to} end={to === "/admin"} onClick={onNav} data-testid={`admin-nav-${to.split("/").pop() || "dashboard"}`}
            className={({ isActive }) => `relative flex items-center gap-3 px-3 py-2 rounded-md text-[13.5px] transition-colors ${isActive ? "bg-white/[0.09] text-white font-semibold before:absolute before:left-0 before:top-1.5 before:bottom-1.5 before:w-[3px] before:rounded-full before:bg-ccn-gold" : "text-white/65 hover:bg-white/[0.06] hover:text-white"}`}>
            {({ isActive }) => <><Icon className={`w-4 h-4 ${isActive ? "text-ccn-teal" : ""}`} />{label}</>}
          </NavLink>
        </div>
      ))}
    </nav>
  );
}

export function AdminLayout() {
  const { user, logout, reload, can } = useAuth();
  const nav = useNavigate();
  const [open, setOpen] = useState(false);
  useEffect(() => { if (user === undefined) reload(); }, [user, reload]);
  if (user === null || user === undefined) return <div className="min-h-screen flex items-center justify-center text-slate-500">Učitavanje…</div>;
  if (!user) return <Navigate to="/admin/prijava" replace />;
  const side = (
    <div className="flex flex-col h-full">
      <Link to="/admin" className="flex items-center gap-3 px-2 mb-2 pb-5 border-b border-white/10"><img src="/icon-192.png" alt="CČN" className="w-11 h-11 rounded-lg ring-1 ring-ccn-gold/40" /><span className="font-serif-news font-black text-white leading-tight text-lg">CČN<br /><span className="text-[11px] font-sans font-semibold tracking-wider uppercase text-ccn-gold">Redakcijski CMS</span></span></Link>
      <div className="flex-1 overflow-y-auto -mx-1 px-1"><SideNav onNav={() => setOpen(false)} /></div>
      <div className="mt-4 pt-4 border-t border-white/10 flex items-center gap-3 px-2">
        <span className="w-9 h-9 rounded-full bg-ccn-teal text-ccn-navy font-bold flex items-center justify-center">{user.name?.[0]}</span>
        <span className="min-w-0"><span className="block text-white text-sm font-semibold truncate">{user.name}</span><span className="block text-[11px] text-white/45 truncate">{user.email}</span></span>
      </div>
    </div>
  );
  return (
    <div className="admin-shell min-h-screen flex bg-[#F2F4F8]">
      <aside className="hidden lg:flex flex-col w-64 shrink-0 bg-ccn-navy p-4 sticky top-0 h-screen">{side}</aside>
      <Sheet open={open} onOpenChange={setOpen}><SheetContent side="left" className="bg-ccn-navy w-72 border-0 p-4 flex flex-col"><SheetTitle className="sr-only">Meni</SheetTitle>{side}</SheetContent></Sheet>
      <div className="flex-1 min-w-0">
        <header className="h-16 bg-white/85 backdrop-blur-md border-b border-[#E3E7EE] flex items-center px-4 md:px-8 gap-4 sticky top-0 z-30">
          <button className="lg:hidden" onClick={() => setOpen(true)} aria-label="Meni" data-testid="admin-mobile-menu"><Menu className="w-5 h-5" /></button>
          {can("articles.create") && <Link to="/admin/clanci/novi" className="hidden sm:inline-flex items-center gap-1.5 bg-ccn-navy text-white text-sm font-semibold px-4 py-2 rounded-full hover:bg-ccn-tealdark transition-colors" data-testid="admin-quick-new"><Plus className="w-4 h-4" />Nova vijest</Link>}
          <div className="flex-1" />
          <a href="/" target="_blank" rel="noreferrer" className="text-sm text-slate-500 hover:text-ccn-navy flex items-center gap-1" data-testid="admin-view-site">Portal <ExternalLink className="w-3 h-3" /></a>
          <Link to="/admin/profil" className="text-sm font-semibold flex items-center gap-1.5" data-testid="admin-profile-link"><Shield className="w-4 h-4 text-ccn-tealdark" />{user.name}</Link>
          <button onClick={async () => { await logout(); nav("/admin/prijava"); }} className="text-slate-500 hover:text-ccn-red" aria-label="Odjava" data-testid="admin-logout"><LogOut className="w-4 h-4" /></button>
        </header>
        <main className="p-4 md:p-8 max-w-[1440px] fade-up"><Outlet /></main>
      </div>
    </div>
  );
}

export function RequirePerm({ perms, children }) {
  const { can } = useAuth();
  if (perms && !can(...perms)) return <div className="p-10 text-center text-slate-500" data-testid="no-permission">Nemate dozvolu za pristup ovom modulu.</div>;
  return children;
}

export function PageHead({ title, children, sub }) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-3 mb-6">
      <div><h1 className="font-serif-news text-2xl md:text-[30px] font-black tracking-tight">{title}</h1>{sub && <p className="text-sm text-slate-500 mt-1.5">{sub}</p>}</div>
      <div className="flex gap-2 flex-wrap">{children}</div>
    </div>
  );
}
