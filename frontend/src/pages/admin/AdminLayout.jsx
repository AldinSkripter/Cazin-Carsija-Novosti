import { useEffect, useState } from "react";
import { Link, NavLink, Navigate, Outlet, useNavigate } from "react-router-dom";
import {
  LayoutDashboard, FileText, FolderTree, Tags, Image, LayoutTemplate, Zap, Megaphone, MessageSquare, Inbox, Mail, Users,
  Video, ScrollText, Settings, BarChart3, FileCode, LogOut, Menu, Shield, ExternalLink,
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

function SideNav({ onNav }) {
  const { can } = useAuth();
  return (
    <nav className="flex flex-col gap-0.5" data-testid="admin-sidebar">
      {NAV.filter(([, , , p]) => !p || can(...p)).map(([to, label, Icon]) => (
        <NavLink key={to} to={to} end={to === "/admin"} onClick={onNav} data-testid={`admin-nav-${to.split("/").pop() || "dashboard"}`}
          className={({ isActive }) => `flex items-center gap-3 px-3 py-2 rounded-sm text-sm transition-colors ${isActive ? "bg-ccn-teal text-ccn-navy font-semibold" : "text-white/75 hover:bg-white/10 hover:text-white"}`}>
          <Icon className="w-4 h-4" />{label}
        </NavLink>
      ))}
    </nav>
  );
}

export function AdminLayout() {
  const { user, logout, reload } = useAuth();
  const nav = useNavigate();
  const [open, setOpen] = useState(false);
  useEffect(() => { if (user === undefined) reload(); }, [user, reload]);
  if (user === null || user === undefined) return <div className="min-h-screen flex items-center justify-center text-slate-500">Učitavanje…</div>;
  if (!user) return <Navigate to="/admin/prijava" replace />;
  const side = (
    <div className="flex flex-col h-full">
      <Link to="/admin" className="flex items-center gap-3 px-2 mb-6"><img src="/icon-192.png" alt="CČN" className="w-10 h-10 rounded" /><span className="font-serif-news font-black text-white leading-tight">CČN<br /><span className="text-[11px] font-sans font-normal text-ccn-gold">Redakcijski CMS</span></span></Link>
      <SideNav onNav={() => setOpen(false)} />
    </div>
  );
  return (
    <div className="min-h-screen flex bg-[#F3F5F9]">
      <aside className="hidden lg:block w-60 shrink-0 bg-ccn-navy p-4 sticky top-0 h-screen overflow-y-auto">{side}</aside>
      <Sheet open={open} onOpenChange={setOpen}><SheetContent side="left" className="bg-ccn-navy w-64 border-0 p-4"><SheetTitle className="sr-only">Meni</SheetTitle>{side}</SheetContent></Sheet>
      <div className="flex-1 min-w-0">
        <header className="h-14 bg-white border-b flex items-center px-4 gap-3 sticky top-0 z-30">
          <button className="lg:hidden" onClick={() => setOpen(true)} aria-label="Meni" data-testid="admin-mobile-menu"><Menu className="w-5 h-5" /></button>
          <div className="flex-1" />
          <a href="/" target="_blank" rel="noreferrer" className="text-sm text-slate-500 hover:text-ccn-navy flex items-center gap-1" data-testid="admin-view-site">Portal <ExternalLink className="w-3 h-3" /></a>
          <Link to="/admin/profil" className="text-sm font-semibold flex items-center gap-1.5" data-testid="admin-profile-link"><Shield className="w-4 h-4 text-ccn-tealdark" />{user.name}</Link>
          <button onClick={async () => { await logout(); nav("/admin/prijava"); }} className="text-slate-500 hover:text-ccn-red" aria-label="Odjava" data-testid="admin-logout"><LogOut className="w-4 h-4" /></button>
        </header>
        <main className="p-4 md:p-8 max-w-[1400px]"><Outlet /></main>
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
      <div><h1 className="font-serif-news text-2xl md:text-3xl font-black">{title}</h1>{sub && <p className="text-sm text-slate-500 mt-1">{sub}</p>}</div>
      <div className="flex gap-2 flex-wrap">{children}</div>
    </div>
  );
}
