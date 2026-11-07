import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, BarChart, Bar, Legend } from "recharts";
import { api, errMsg, fmtDate, BACKEND } from "../../lib/api";
import { PageHead } from "./AdminLayout";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Textarea } from "../../components/ui/textarea";
import { Switch } from "../../components/ui/switch";
import { Redirects } from "./CrudPages";

const S = ({ title, children }) => <div className="bg-white border rounded-md p-5"><h2 className="font-bold mb-3">{title}</h2><div className="grid gap-2">{children}</div></div>;

function MenuEditor({ value = [], onChange, tid }) {
  return (
    <div className="grid gap-1" data-testid={tid}>
      {value.map((m, i) => (
        <div key={i} className="flex gap-1">
          <Input value={m.label} onChange={(e) => onChange(value.map((x, j) => (j === i ? { ...x, label: e.target.value } : x)))} placeholder="Naziv" />
          <Input value={m.url} onChange={(e) => onChange(value.map((x, j) => (j === i ? { ...x, url: e.target.value } : x)))} placeholder="/kategorija/…" />
          <Button size="sm" variant="ghost" onClick={() => onChange(value.filter((_, j) => j !== i))}>✕</Button>
        </div>
      ))}
      <Button size="sm" variant="outline" onClick={() => onChange([...value, { label: "", url: "/" }])}>+ stavka</Button>
    </div>
  );
}

export default function SettingsPage() {
  const [s, setS] = useState(null);
  const [priv, setPriv] = useState([]);
  const [ai, setAi] = useState(null);
  const fileRef = useRef();
  useEffect(() => {
    api.get("/admin/settings").then((r) => setS(r.data));
    api.get("/admin/privacy-requests").then((r) => setPriv(r.data));
    api.get("/admin/ai/usage").then((r) => setAi(r.data));
  }, []);
  if (!s) return <p>Učitavanje…</p>;
  const set = (k, v) => setS({ ...s, [k]: v });
  const txt = (k, l, ph) => <label className="text-xs font-semibold grid gap-1">{l}<Input value={s[k] || ""} onChange={(e) => set(k, e.target.value)} placeholder={ph} data-testid={`setting-${k}`} /></label>;
  const sw = (k, l) => <label className="flex justify-between items-center text-sm">{l}<Switch checked={!!s[k]} onCheckedChange={(v) => set(k, v)} data-testid={`setting-${k}`} /></label>;
  const save = async () => { try { const { data } = await api.put("/admin/settings", s); setS(data); toast.success("Postavke sačuvane"); } catch (e) { toast.error(errMsg(e)); } };
  const restore = async (file) => {
    if (!file || !window.confirm("Vraćanje backupa zamjenjuje postojeće podatke. Nastaviti?")) return;
    const fd = new FormData(); fd.append("file", file);
    try { const { data } = await api.post("/admin/restore", fd); toast.success(`Vraćeno: ${Object.keys(data.restored).length} kolekcija`); } catch (e) { toast.error(errMsg(e)); }
  };
  return (
    <div data-testid="admin-settings">
      <PageHead title="Sistemske postavke"><Button className="bg-ccn-navy" onClick={save} data-testid="settings-save">Sačuvaj postavke</Button></PageHead>
      <div className="grid lg:grid-cols-2 gap-5">
        <S title="Portal i brend">{txt("site_name", "Naziv portala")}{txt("tagline", "Slogan")}{txt("publisher_name", "Izdavač (Schema.org / Google News)")}{txt("logo_url", "Logo URL")}{txt("logo_mobile_url", "Mobilni logo URL")}{txt("favicon_url", "Favicon URL")}{txt("social_image", "Zadana društvena slika")}{txt("site_url", "Javna domena (npr. https://cazincarsija.ba)")}</S>
        <S title="Kontakt i društvene mreže">{txt("contact_email", "Kontakt e-mail")}{txt("phone", "Telefon")}{txt("address", "Adresa")}
          {["facebook", "instagram", "youtube", "tiktok", "x"].map((k) => <label key={k} className="text-xs font-semibold grid gap-1 capitalize">{k}<Input value={s.social?.[k] || ""} onChange={(e) => set("social", { ...s.social, [k]: e.target.value })} placeholder="https://…" /></label>)}</S>
        <S title="Glavni meni"><MenuEditor value={s.main_menu} onChange={(v) => set("main_menu", v)} tid="menu-editor" /></S>
        <S title="Footer"><MenuEditor value={s.footer_menu} onChange={(v) => set("footer_menu", v)} tid="footer-menu-editor" /><Textarea value={s.footer_text || ""} onChange={(e) => set("footer_text", e.target.value)} rows={2} /></S>
        <S title="SEO i analitika">{txt("google_site_verification", "Google Search Console verifikacija")}{txt("ga4_id", "GA4 Measurement ID", "G-XXXXXXX")}{txt("plausible_domain", "Plausible domena (privatnosno orijentisana analitika)")}{txt("adsense_client", "AdSense client ID", "ca-pub-…")}
          <p className="text-xs text-slate-500">GA4 i Plausible se učitavaju samo uz pristanak posjetioca na analitičke kolačiće. Sitemap: <a className="underline" href={`${BACKEND}/api/sitemap.xml`} target="_blank" rel="noreferrer">/api/sitemap.xml</a> · Google News: <a className="underline" href={`${BACKEND}/api/news-sitemap.xml`} target="_blank" rel="noreferrer">/api/news-sitemap.xml</a> · <a className="underline" href={`${BACKEND}/api/rss.xml`} target="_blank" rel="noreferrer">RSS</a> · <a className="underline" href={`${BACKEND}/api/robots.txt`} target="_blank" rel="noreferrer">robots.txt</a> · <a className="underline" href={`${BACKEND}/api/docs`} target="_blank" rel="noreferrer">API dokumentacija (OpenAPI)</a></p></S>
        <S title="Komentari, prikaz i moduli">{sw("comments_enabled", "Komentari uključeni")}{sw("comments_require_approval", "Komentari zahtijevaju odobrenje")}{sw("show_views", "Javno prikazivanje broja pregleda")}{sw("newsletter_enabled", "Newsletter")}{sw("ai_enabled", "AI asistent")}{sw("maintenance_mode", "Način održavanja (portal nedostupan javnosti)")}{txt("maintenance_message", "Poruka održavanja")}</S>
        <S title="Backup i vraćanje podataka">
          <p className="text-xs text-slate-500">Preuzmite kompletan JSON backup (članci, korisnici, postavke, mediji – metapodaci). Fotografije su u objektnom skladištu.</p>
          <a href={`${BACKEND}/api/admin/backup`} data-testid="backup-download"><Button variant="outline" className="w-full">Preuzmi backup</Button></a>
          <input ref={fileRef} type="file" accept="application/json" className="hidden" onChange={(e) => restore(e.target.files[0])} />
          <Button variant="outline" className="text-ccn-red" onClick={() => fileRef.current.click()} data-testid="backup-restore">Vrati iz backupa…</Button>
        </S>
        <S title={`AI korištenje i troškovi${ai ? ` – ukupno ~$${ai.total_cost_usd}` : ""}`}>
          <div className="max-h-48 overflow-y-auto text-xs" data-testid="ai-usage">{ai?.items.map((i) => <p key={i.id} className="py-1 border-b">{fmtDate(i.created_at)} · {i.user_name} · {i.action} · ~${i.est_cost_usd}</p>)}{!ai?.items.length && "Nema korištenja."}</div>
        </S>
        <S title="Zahtjevi za privatnost (pristup / brisanje)">
          {priv.map((p) => <p key={p.id} className="text-xs py-1 border-b flex justify-between"><span>{p.email} · {p.type} · {p.status} · {fmtDate(p.created_at)}</span>{p.status !== "done" && <button className="text-ccn-tealdark" onClick={() => api.post(`/admin/privacy-requests/${p.id}`, { status: "done" }).then(() => setPriv(priv.map((x) => (x.id === p.id ? { ...x, status: "done" } : x))))}>Riješeno</button>}</p>)}
          {!priv.length && <p className="text-xs text-slate-500">Nema zahtjeva.</p>}
        </S>
      </div>
      <div className="mt-8"><Redirects /></div>
    </div>
  );
}

export function Audit() {
  const [d, setD] = useState({ items: [], total: 0 });
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  useEffect(() => { api.get("/admin/audit", { params: { q, page } }).then((r) => setD(r.data)); }, [q, page]);
  return (
    <div data-testid="admin-audit">
      <PageHead title="Audit log" sub={`${d.total} događaja`}><Input placeholder="Filter (akcija, korisnik…)" value={q} onChange={(e) => { setQ(e.target.value); setPage(1); }} data-testid="audit-search" /></PageHead>
      <div className="bg-white border rounded-md overflow-x-auto">
        <table className="w-full text-sm"><thead className="bg-slate-50 text-left text-xs uppercase text-slate-500"><tr><th className="p-3">Vrijeme</th><th className="p-3">Korisnik</th><th className="p-3">Akcija</th><th className="p-3">Detalji</th><th className="p-3">IP</th></tr></thead>
          <tbody>{d.items.map((l) => <tr key={l.id} className="border-t"><td className="p-3 whitespace-nowrap text-slate-500">{fmtDate(l.created_at)}</td><td className="p-3 font-semibold">{l.user_name}</td><td className="p-3"><code className="text-xs">{l.action}</code></td><td className="p-3 max-w-md truncate">{l.details}</td><td className="p-3 text-xs text-slate-400">{l.ip}</td></tr>)}</tbody></table>
      </div>
      <div className="flex gap-2 mt-3"><Button variant="outline" disabled={page === 1} onClick={() => setPage(page - 1)}>‹</Button><Button variant="outline" disabled={page * 50 >= d.total} onClick={() => setPage(page + 1)}>›</Button></div>
    </div>
  );
}

function Bars({ title, data, k = "name" }) {
  return (
    <div className="bg-white border rounded-md p-5"><h2 className="font-bold mb-3">{title}</h2>
      <div className="h-56"><ResponsiveContainer><BarChart data={data} layout="vertical"><XAxis type="number" fontSize={11} /><YAxis type="category" dataKey={k} width={130} fontSize={11} /><Tooltip /><Bar dataKey="count" name="Prikazi" fill="#00C2B8" /></BarChart></ResponsiveContainer></div>
    </div>
  );
}

export function Analytics() {
  const [d, setD] = useState(null);
  const [days, setDays] = useState(30);
  useEffect(() => { api.get("/admin/analytics", { params: { days } }).then((r) => setD(r.data)); }, [days]);
  if (!d) return <p>Učitavanje…</p>;
  return (
    <div data-testid="admin-analytics">
      <PageHead title="Statistika" sub="Prikazi stranica ≠ sesije ≠ korisnici. Korisnici = anonimni ID preglednika (bez kolačića za praćenje).">
        <select value={days} onChange={(e) => setDays(Number(e.target.value))} className="border rounded-sm px-3 py-2 text-sm bg-white" data-testid="analytics-days"><option value={7}>7 dana</option><option value={30}>30 dana</option><option value={90}>90 dana</option><option value={365}>Godina</option></select>
      </PageHead>
      <div className="grid grid-cols-3 gap-3 mb-5">
        {[["Prikazi stranica", d.totals.pageviews], ["Sesije", d.totals.sessions], ["Korisnici", d.totals.users]].map(([l, v]) => <div key={l} className="bg-white border rounded-md p-4" data-testid={`analytics-${l}`}><p className="text-3xl font-bold">{v}</p><p className="text-xs uppercase text-slate-500">{l}</p></div>)}
      </div>
      <div className="bg-white border rounded-md p-5 mb-5"><h2 className="font-bold mb-3">Trend po danima</h2>
        <div className="h-64"><ResponsiveContainer><LineChart data={d.per_day}><CartesianGrid strokeDasharray="3 3" stroke="#E6E9EF" /><XAxis dataKey="day" fontSize={11} /><YAxis fontSize={11} /><Tooltip /><Legend />
          <Line dataKey="pageviews" name="Prikazi" stroke="#0B1F3B" /><Line dataKey="sessions" name="Sesije" stroke="#00C2B8" /><Line dataKey="users" name="Korisnici" stroke="#D4A52C" /></LineChart></ResponsiveContainer></div>
      </div>
      <div className="grid lg:grid-cols-2 gap-5">
        <Bars title="Najčitanije vijesti" data={d.top_articles} k="title" /><Bars title="Posjete po kategoriji" data={d.by_category} />
        <Bars title="Posjete po autoru" data={d.by_author} /><Bars title="Izvori saobraćaja" data={d.sources} />
        <Bars title="Mobilni / desktop" data={d.devices} /><Bars title="Najpopularnije teme" data={d.top_tags} />
      </div>
      <div className="bg-white border rounded-md p-5 mt-5" data-testid="analytics-ads"><h2 className="font-bold mb-3">Učinak reklamnih pozicija</h2>
        <table className="w-full text-sm"><thead className="text-left text-xs uppercase text-slate-500"><tr><th>Kampanja</th><th>Pozicija</th><th>Prikazi</th><th>Klikovi</th><th>CTR</th></tr></thead>
          <tbody>{d.ads.map((a) => <tr key={a.name} className="border-t"><td className="py-2">{a.name}</td><td>{a.position}</td><td>{a.impression}</td><td>{a.click}</td><td>{a.ctr}%</td></tr>)}</tbody></table>
        {!d.ads.length && <p className="text-sm text-slate-500">Nema podataka.</p>}
      </div>
    </div>
  );
}
