import { useEffect, useState } from "react";
import { Plus, Pencil, Trash2, ImagePlus } from "lucide-react";
import { toast } from "sonner";
import { api, errMsg, mediaUrl, fmtDate, AD_POSITIONS } from "../../lib/api";
import { useAuth } from "../../lib/auth";
import { PageHead } from "./AdminLayout";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Textarea } from "../../components/ui/textarea";
import { Switch } from "../../components/ui/switch";
import { Dialog, DialogContent, DialogTitle } from "../../components/ui/dialog";
import { MediaPicker } from "./Media";
import { toLocal, fromLocal } from "./ArticleEditor";

function Field({ f, value, onChange, opts }) {
  const [pick, setPick] = useState(false);
  const tid = `field-${f.key}`;
  if (f.type === "bool") return <label className="flex items-center justify-between text-sm">{f.label}<Switch checked={!!value} onCheckedChange={onChange} data-testid={tid} /></label>;
  const label = <span className="text-xs font-semibold">{f.label}</span>;
  if (f.type === "textarea" || f.type === "html") return <label className="grid gap-1">{label}<Textarea rows={f.type === "html" ? 10 : 3} value={value || ""} onChange={(e) => onChange(e.target.value)} data-testid={tid} />{f.help && <span className="text-[11px] text-slate-500">{f.help}</span>}</label>;
  if (f.type === "select") {
    const list = f.options || opts[f.key] || [];
    return <label className="grid gap-1">{label}<select value={value ?? ""} onChange={(e) => onChange(e.target.value || null)} className="border rounded-sm px-3 py-2 text-sm" data-testid={tid}><option value="">—</option>{list.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select></label>;
  }
  if (f.type === "datetime") return <label className="grid gap-1">{label}<Input type="datetime-local" value={toLocal(value)} onChange={(e) => onChange(fromLocal(e.target.value) || "")} data-testid={tid} /></label>;
  if (f.type === "image") return (
    <label className="grid gap-1">{label}
      <div className="flex gap-2"><Input value={value || ""} onChange={(e) => onChange(e.target.value)} placeholder="URL ili odaberite iz biblioteke" data-testid={tid} /><Button type="button" variant="outline" onClick={() => setPick(true)}><ImagePlus className="w-4 h-4" /></Button></div>
      {value && <img src={mediaUrl(value)} alt="" className="h-16 object-contain self-start" />}
      <MediaPicker open={pick} onClose={() => setPick(false)} onPick={(m) => onChange(m.large)} />
    </label>
  );
  return <label className="grid gap-1">{label}<Input type={f.type === "number" ? "number" : "text"} value={value ?? ""} onChange={(e) => onChange(f.type === "number" ? Number(e.target.value) : e.target.value)} data-testid={tid} />{f.help && <span className="text-[11px] text-slate-500">{f.help}</span>}</label>;
}

export function CrudPage({ title, sub, endpoint, fields, columns, defaults = {}, optionLoaders = {}, testid, hideFields }) {
  const [items, setItems] = useState([]);
  const [edit, setEdit] = useState(null);
  const [opts, setOpts] = useState({});
  const { can } = useAuth();
  const load = () => api.get(`/admin/${endpoint}`).then((r) => setItems(r.data)).catch((e) => toast.error(errMsg(e)));
  useEffect(() => {
    load();
    Object.entries(optionLoaders).forEach(([k, fn]) => fn().then((o) => setOpts((x) => ({ ...x, [k]: o }))));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [endpoint]);
  const save = async () => {
    try {
      if (edit.id) await api.put(`/admin/${endpoint}/${edit.id}`, edit); else await api.post(`/admin/${endpoint}`, edit);
      toast.success("Sačuvano"); setEdit(null); load();
    } catch (e) { toast.error(errMsg(e)); }
  };
  const del = async (it) => {
    if (!window.confirm("Obrisati stavku?")) return;
    try { await api.delete(`/admin/${endpoint}/${it.id}`); toast.success("Obrisano"); load(); } catch (e) { toast.error(errMsg(e)); }
  };
  const show = (v, c) => {
    if (c.render) return c.render(v, opts);
    if (typeof v === "boolean") return v ? "✓" : "—";
    if (c.type === "date") return fmtDate(v);
    return String(v ?? "");
  };
  const visible = fields.filter((f) => !hideFields?.(edit || {}, f, can));
  return (
    <div data-testid={testid}>
      <PageHead title={title} sub={sub}><Button className="bg-ccn-navy" onClick={() => setEdit({ ...defaults })} data-testid={`${testid}-add`}><Plus className="w-4 h-4 mr-1" />Dodaj</Button></PageHead>
      <div className="bg-white border rounded-md overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-left text-xs uppercase text-slate-500"><tr>{columns.map((c) => <th key={c.key} className="p-3">{c.label}</th>)}<th className="p-3 w-24" /></tr></thead>
          <tbody>
            {items.map((it) => (
              <tr key={it.id} className="border-t hover:bg-slate-50" data-testid={`${testid}-row-${it.id}`}>
                {columns.map((c) => <td key={c.key} className="p-3">{show(it[c.key], c)}</td>)}
                <td className="p-3 whitespace-nowrap">
                  <button onClick={() => setEdit({ ...it })} className="p-1.5 hover:text-ccn-tealdark" aria-label="Uredi" data-testid={`${testid}-edit-${it.id}`}><Pencil className="w-4 h-4" /></button>
                  <button onClick={() => del(it)} className="p-1.5 hover:text-ccn-red" aria-label="Obriši" data-testid={`${testid}-delete-${it.id}`}><Trash2 className="w-4 h-4" /></button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!items.length && <p className="p-8 text-center text-slate-500">Nema stavki.</p>}
      </div>
      <Dialog open={!!edit} onOpenChange={() => setEdit(null)}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto" data-testid={`${testid}-dialog`}>
          <DialogTitle>{edit?.id ? "Uredi" : "Dodaj"} – {title}</DialogTitle>
          {edit && <div className="grid gap-3">{visible.map((f) => <Field key={f.key} f={f} value={edit[f.key]} opts={opts} onChange={(v) => setEdit({ ...edit, [f.key]: v })} />)}</div>}
          <Button onClick={save} className="bg-ccn-navy" data-testid={`${testid}-save`}>Sačuvaj</Button>
        </DialogContent>
      </Dialog>
    </div>
  );
}

const catOpts = () => api.get("/admin/categories").then((r) => r.data.map((c) => [c.id, c.name]));
const artOpts = () => api.get("/admin/articles", { params: { status: "published", limit: 100 } }).then((r) => r.data.items.map((a) => [a.id, a.title]));
const advOpts = () => api.get("/admin/advertisers").then((r) => r.data.map((a) => [a.id, a.name]));

export const Categories = () => (
  <CrudPage title="Kategorije" sub="Neograničen broj kategorija i podkategorija" endpoint="categories" testid="categories" optionLoaders={{ parent_id: catOpts }}
    defaults={{ visible: true, show_in_menu: false, order: 100 }}
    columns={[{ key: "name", label: "Naziv" }, { key: "slug", label: "Slug" }, { key: "parent_id", label: "Nadkategorija", render: (v, o) => (o.parent_id || []).find(([id]) => id === v)?.[1] || "—" }, { key: "visible", label: "Vidljiva" }, { key: "show_in_menu", label: "U meniju" }, { key: "order", label: "Redoslijed" }]}
    fields={[{ key: "name", label: "Naziv" }, { key: "slug", label: "Slug (prazno = automatski)" }, { key: "parent_id", label: "Nadkategorija", type: "select" }, { key: "description", label: "Opis", type: "textarea" },
      { key: "seo_title", label: "SEO naslov" }, { key: "seo_description", label: "SEO opis", type: "textarea" }, { key: "image", label: "Slika", type: "image" },
      { key: "color", label: "Boja (#hex)" }, { key: "order", label: "Redoslijed", type: "number" }, { key: "visible", label: "Vidljiva", type: "bool" }, { key: "show_in_menu", label: "Prikaži u meniju (uredite meni u Postavkama)", type: "bool" }]} />
);

export const TagsPage = () => (
  <CrudPage title="Oznake" endpoint="tags" testid="tags" columns={[{ key: "name", label: "Naziv" }, { key: "slug", label: "Slug" }]}
    fields={[{ key: "name", label: "Naziv" }, { key: "description", label: "Opis", type: "textarea" }]} />
);

export const Breaking = () => (
  <CrudPage title="Breaking News" sub="Crvena traka hitnih vijesti na vrhu portala" endpoint="breaking" testid="breaking" optionLoaders={{ article_id: artOpts }}
    defaults={{ active: true, priority: 5 }}
    columns={[{ key: "title", label: "Naslov" }, { key: "priority", label: "Prioritet" }, { key: "active", label: "Aktivno" }, { key: "start_at", label: "Početak", type: "date" }, { key: "end_at", label: "Kraj", type: "date" }, { key: "created_by", label: "Objavio" }]}
    fields={[{ key: "title", label: "Hitni naslov" }, { key: "article_id", label: "Povezani članak", type: "select" }, { key: "url", label: "Ili vanjski/interni link" },
      { key: "priority", label: "Prioritet (1-10, viši ide prvi)", type: "number" }, { key: "start_at", label: "Početak prikaza", type: "datetime" }, { key: "end_at", label: "Kraj prikaza", type: "datetime" }, { key: "active", label: "Aktivno", type: "bool" }]} />
);

export function Ads() {
  const [tab, setTab] = useState("campaigns");
  return (
    <div>
      <div className="flex gap-2 mb-4">{[["campaigns", "Kampanje"], ["advertisers", "Oglašivači"]].map(([k, l]) => <Button key={k} variant={tab === k ? "default" : "outline"} onClick={() => setTab(k)} data-testid={`ads-tab-${k}`}>{l}</Button>)}</div>
      {tab === "advertisers" ? (
        <CrudPage title="Oglašivači" endpoint="advertisers" testid="advertisers" columns={[{ key: "name", label: "Naziv" }, { key: "contact", label: "Kontakt" }, { key: "email", label: "E-mail" }]}
          fields={[{ key: "name", label: "Naziv" }, { key: "contact", label: "Kontakt osoba" }, { key: "email", label: "E-mail" }, { key: "phone", label: "Telefon" }, { key: "notes", label: "Napomene", type: "textarea" }]} />
      ) : (
        <CrudPage title="Reklamne kampanje" sub="Prikazi i klikovi se broje automatski" endpoint="campaigns" testid="campaigns" optionLoaders={{ advertiser_id: advOpts }}
          defaults={{ type: "image", active: true, weight: 1, position: "sidebar", sponsored_label: "Oglas" }}
          hideFields={(e, f, can) => f.key === "html_code" && (e.type === "image" || !can("settings.manage"))}
          columns={[{ key: "name", label: "Naziv" }, { key: "position", label: "Pozicija", render: (v) => AD_POSITIONS[v] || v }, { key: "active", label: "Aktivna" }, { key: "impressions", label: "Prikazi" }, { key: "clicks", label: "Klikovi" },
            { key: "max_impressions", label: "Limit prikaza" }, { key: "end_at", label: "Kraj", type: "date" }]}
          fields={[{ key: "name", label: "Naziv kampanje" }, { key: "advertiser_id", label: "Oglašivač", type: "select" }, { key: "position", label: "Pozicija", type: "select", options: Object.entries(AD_POSITIONS) },
            { key: "type", label: "Tip", type: "select", options: [["image", "Banner (slika)"], ["html", "HTML kod (samo Super Admin)"], ["adsense", "Google AdSense / Ad Manager (samo Super Admin)"]] },
            { key: "image_url", label: "Banner", type: "image" }, { key: "mobile_image_url", label: "Mobilni banner (opcionalno)", type: "image" }, { key: "alt", label: "ALT tekst bannera" },
            { key: "target_url", label: "Odredišni URL (https://…)" }, { key: "html_code", label: "Vanjski reklamni kod", type: "textarea", help: "Prikazuje se u izolovanom (sandbox) okviru – ne može pristupiti portalu ni sesijama." },
            { key: "start_at", label: "Početak", type: "datetime" }, { key: "end_at", label: "Kraj", type: "datetime" }, { key: "max_impressions", label: "Ograničenje prikaza (0 = bez)", type: "number" },
            { key: "weight", label: "Težina rotacije", type: "number" }, { key: "sponsored_label", label: "Oznaka (Oglas / Sponzorisano)" }, { key: "active", label: "Aktivna", type: "bool" }]} />
      )}
    </div>
  );
}

export const PagesAdmin = () => (
  <CrudPage title="Stranice" sub="O nama, Impressum, Politika privatnosti… (HTML sadržaj, sanitizovan)" endpoint="pages" testid="pages" defaults={{ published: true }}
    columns={[{ key: "title", label: "Naslov" }, { key: "slug", label: "URL", render: (v) => `/stranica/${v}` }, { key: "published", label: "Objavljeno" }]}
    fields={[{ key: "title", label: "Naslov" }, { key: "slug", label: "Slug" }, { key: "content", label: "Sadržaj (HTML: <p>, <h2>, <a>, <ul>…)", type: "html" }, { key: "seo_title", label: "SEO naslov" }, { key: "seo_description", label: "SEO opis" }, { key: "published", label: "Objavljeno", type: "bool" }]} />
);

export const Cameras = () => (
  <CrudPage title="Live kamere" sub="Kamere sa graničnih prijelaza – slika se dohvaća preko servera i automatski osvježava" endpoint="cameras" testid="cameras" defaults={{ active: true, refresh_seconds: 60, order: 10 }}
    columns={[{ key: "name", label: "Naziv" }, { key: "group", label: "Grupa" }, { key: "location", label: "Lokacija" }, { key: "refresh_seconds", label: "Osvježavanje (s)" }, { key: "active", label: "Aktivna" }, { key: "order", label: "Redoslijed" }]}
    fields={[{ key: "name", label: "Naziv (npr. GP Maljevac – Ulaz u HR iz BiH)" }, { key: "location", label: "Lokacija" }, { key: "group", label: "Grupa", type: "select", options: ["Granica BiH – Hrvatska", "Granica sa Slovenijom", "Granica sa Srbijom", "Granica sa Crnom Gorom", "Ostalo"].map((g) => [g, g]) }, { key: "image_url", label: "URL slike kamere (JPG snapshot)", help: "HAK primjer: https://m.hak.hr/cam.asp?id=429" },
      { key: "page_url", label: "Izvorna stranica kamere" }, { key: "description", label: "Opis / izvor" }, { key: "refresh_seconds", label: "Osvježavanje (sekundi, min 15)", type: "number" }, { key: "order", label: "Redoslijed", type: "number" }, { key: "active", label: "Aktivna", type: "bool" }]} />
);

export const Redirects = () => (
  <CrudPage title="301 Redirekcije" sub="Automatski se kreiraju kad se promijeni slug objavljenog članka" endpoint="redirects" testid="redirects" defaults={{ code: 301 }}
    columns={[{ key: "from_path", label: "Sa" }, { key: "to_path", label: "Na" }, { key: "code", label: "Kod" }]}
    fields={[{ key: "from_path", label: "Stara putanja (npr. /vijesti/stari-slug)" }, { key: "to_path", label: "Nova putanja" }, { key: "code", label: "Kod", type: "number" }]} />
);
