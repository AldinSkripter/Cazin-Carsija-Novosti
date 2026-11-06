import { useEffect, useState } from "react";
import { ArrowUp, ArrowDown, Eye, EyeOff, Trash2, Plus, Globe } from "lucide-react";
import { toast } from "sonner";
import { api, errMsg, AD_POSITIONS } from "../../lib/api";
import { PageHead } from "./AdminLayout";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";

const TYPES = { hero: "Glavna izdvojena vijest", latest: "Najnovije vijesti", most_read: "Najčitanije", category: "Kategorija", manual: "Ručno odabrani članci",
  video: "Video vijesti", gallery: "Foto galerije", ad: "Reklamna pozicija", cameras: "Live kamere", weather: "Vremenska prognoza", popular_tags: "Popularne teme" };

export default function HomeBuilder() {
  const [blocks, setBlocks] = useState([]);
  const [cats, setCats] = useState([]);
  const [arts, setArts] = useState([]);
  const [newType, setNewType] = useState("category");
  useEffect(() => {
    api.get("/admin/homepage").then((r) => setBlocks(r.data.draft || []));
    api.get("/public/categories").then((r) => setCats(r.data));
    api.get("/admin/articles", { params: { status: "published", limit: 100 } }).then((r) => setArts(r.data.items));
  }, []);
  const upd = (i, patch) => setBlocks(blocks.map((b, j) => (j === i ? { ...b, ...patch } : b)));
  const move = (i, d) => { const n = [...blocks]; const j = i + d; if (j < 0 || j >= n.length) return; [n[i], n[j]] = [n[j], n[i]]; setBlocks(n); };
  const saveDraft = async () => { try { await api.put("/admin/homepage", { blocks }); toast.success("Nacrt sačuvan"); return true; } catch (e) { toast.error(errMsg(e)); return false; } };
  const preview = async () => { if (await saveDraft()) window.open("/?preview=1", "_blank"); };
  const publish = async () => { if (!(await saveDraft())) return; await api.post("/admin/homepage/publish"); toast.success("Početna stranica objavljena"); };
  return (
    <div data-testid="home-builder">
      <PageHead title="Početna stranica" sub="Dodajte, premjestite, sakrijte blokove. Promjene su nacrt dok ih ne objavite.">
        <Button variant="outline" onClick={saveDraft} data-testid="home-save-draft">Sačuvaj nacrt</Button>
        <Button variant="outline" onClick={preview} data-testid="home-preview"><Eye className="w-4 h-4 mr-1" />Pregled</Button>
        <Button className="bg-ccn-teal text-ccn-navy hover:bg-ccn-gold" onClick={publish} data-testid="home-publish"><Globe className="w-4 h-4 mr-1" />Objavi</Button>
      </PageHead>
      <div className="grid gap-2">
        {blocks.map((b, i) => (
          <div key={b.id || i} className={`bg-white border rounded-md p-3 grid md:grid-cols-12 gap-2 items-center ${b.visible === false ? "opacity-50" : ""}`} data-testid={`home-block-row-${i}`}>
            <div className="md:col-span-2 text-xs font-bold uppercase text-ccn-tealdark">{TYPES[b.type]}</div>
            <Input className="md:col-span-3" value={b.title || ""} onChange={(e) => upd(i, { title: e.target.value })} placeholder="Naslov bloka" data-testid={`home-block-title-${i}`} />
            <div className="md:col-span-4 flex gap-2">
              {b.type === "category" && <select value={b.category_slug || ""} onChange={(e) => upd(i, { category_slug: e.target.value })} className="border rounded-sm px-2 py-2 text-sm flex-1" data-testid={`home-block-category-${i}`}>{cats.map((c) => <option key={c.id} value={c.slug}>{c.name}</option>)}</select>}
              {b.type === "ad" && <select value={b.ad_position || ""} onChange={(e) => upd(i, { ad_position: e.target.value })} className="border rounded-sm px-2 py-2 text-sm flex-1">{Object.entries(AD_POSITIONS).map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select>}
              {b.type === "manual" && <select multiple value={b.article_ids || []} onChange={(e) => upd(i, { article_ids: [...e.target.selectedOptions].map((o) => o.value) })} className="border rounded-sm px-2 py-1 text-xs flex-1 h-20" data-testid={`home-block-articles-${i}`}>{arts.map((a) => <option key={a.id} value={a.id}>{a.title}</option>)}</select>}
              {["latest", "category", "video", "gallery", "most_read"].includes(b.type) && <Input type="number" min={1} max={24} value={b.limit || 6} onChange={(e) => upd(i, { limit: Number(e.target.value) })} className="w-20" aria-label="Broj članaka" data-testid={`home-block-limit-${i}`} />}
            </div>
            <div className="md:col-span-3 flex gap-1 justify-end">
              <Button size="icon" variant="ghost" onClick={() => move(i, -1)} aria-label="Gore" data-testid={`home-block-up-${i}`}><ArrowUp className="w-4 h-4" /></Button>
              <Button size="icon" variant="ghost" onClick={() => move(i, 1)} aria-label="Dolje" data-testid={`home-block-down-${i}`}><ArrowDown className="w-4 h-4" /></Button>
              <Button size="icon" variant="ghost" onClick={() => upd(i, { visible: b.visible === false })} aria-label="Sakrij" data-testid={`home-block-toggle-${i}`}>{b.visible === false ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}</Button>
              <Button size="icon" variant="ghost" onClick={() => setBlocks(blocks.filter((_, j) => j !== i))} aria-label="Ukloni" data-testid={`home-block-remove-${i}`}><Trash2 className="w-4 h-4 text-ccn-red" /></Button>
            </div>
          </div>
        ))}
      </div>
      <div className="flex gap-2 mt-4">
        <select value={newType} onChange={(e) => setNewType(e.target.value)} className="border rounded-sm px-3 py-2 text-sm bg-white" data-testid="home-new-block-type">{Object.entries(TYPES).map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select>
        <Button variant="outline" onClick={() => setBlocks([...blocks, { type: newType, title: TYPES[newType], limit: 4, visible: true, category_slug: cats[0]?.slug, ad_position: "home_top", dedupe: true }])} data-testid="home-add-block"><Plus className="w-4 h-4 mr-1" />Dodaj blok</Button>
      </div>
    </div>
  );
}
