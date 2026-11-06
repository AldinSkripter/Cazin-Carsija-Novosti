import { useEffect, useRef, useState } from "react";
import { Upload, Trash2, Crop, Check } from "lucide-react";
import { toast } from "sonner";
import { api, errMsg, mediaUrl } from "../../lib/api";
import { Dialog, DialogContent, DialogTitle } from "../../components/ui/dialog";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";

export const snap = (m) => ({ id: m.id, large: m.large, medium: m.medium, thumb: m.thumb, alt: m.alt, caption: m.caption, credit: m.credit });

function MetaEditor({ m, onSaved, onClose }) {
  const [f, setF] = useState({ alt: m.alt || "", caption: m.caption || "", credit: m.credit || "", source: m.source || "", category: m.category || "" });
  const [usage, setUsage] = useState([]);
  useEffect(() => { api.get(`/admin/media/${m.id}/usage`).then((r) => setUsage(r.data)).catch(() => {}); }, [m.id]);
  const save = async () => { const { data } = await api.put(`/admin/media/${m.id}`, f); toast.success("Sačuvano"); onSaved(data); };
  const del = async () => {
    if (!window.confirm("Obrisati fotografiju?")) return;
    try { await api.delete(`/admin/media/${m.id}`); toast.success("Obrisano"); onSaved(null); onClose(); } catch (e) { toast.error(errMsg(e)); }
  };
  const crop = async (ratio) => {
    const w = m.width, h = m.height;
    let cw = w, ch = Math.round(w / ratio);
    if (ch > h) { ch = h; cw = Math.round(h * ratio); }
    try { await api.post(`/admin/media/${m.id}/crop`, { x: (w - cw) / 2, y: (h - ch) / 2, w: cw, h: ch }); toast.success("Kreirana izrezana kopija"); onSaved(m); }
    catch (e) { toast.error(errMsg(e)); }
  };
  return (
    <div className="grid md:grid-cols-2 gap-5" data-testid="media-meta-editor">
      <div>
        <img src={mediaUrl(m.medium)} alt={m.alt} className="w-full rounded-sm" />
        <p className="text-xs text-slate-500 mt-2">{m.width}×{m.height}px · WebP varijante: large / medium / thumb · EXIF uklonjen</p>
        <div className="flex gap-2 mt-2 flex-wrap">
          {[["16:9", 16 / 9], ["4:3", 4 / 3], ["1:1", 1]].map(([l, r]) => <Button key={l} size="sm" variant="outline" onClick={() => crop(r)} data-testid={`crop-${l}`}><Crop className="w-3 h-3 mr-1" />{l}</Button>)}
        </div>
        <p className="text-xs mt-3 font-semibold">Koristi se u {usage.length} članak(a)</p>
        {usage.map((u) => <p key={u.id} className="text-xs text-slate-500">• {u.title}</p>)}
      </div>
      <div className="grid gap-2 content-start">
        {[["alt", "ALT tekst (opis za pristupačnost)"], ["caption", "Opis fotografije"], ["credit", "Autor / autorska prava"], ["source", "Izvor"], ["category", "Kategorija (npr. sport)"]].map(([k, l]) => (
          <label key={k} className="text-xs font-semibold">{l}<Input value={f[k]} onChange={(e) => setF({ ...f, [k]: e.target.value })} data-testid={`media-${k}`} /></label>
        ))}
        <div className="flex gap-2 mt-2">
          <Button onClick={save} className="bg-ccn-navy" data-testid="media-save">Sačuvaj</Button>
          <Button variant="outline" onClick={del} className="text-ccn-red" data-testid="media-delete"><Trash2 className="w-4 h-4" /></Button>
        </div>
      </div>
    </div>
  );
}

export function MediaLibrary({ onPick, multi = false }) {
  const [items, setItems] = useState([]);
  const [q, setQ] = useState("");
  const [cat, setCat] = useState("");
  const [busy, setBusy] = useState(false);
  const [drag, setDrag] = useState(false);
  const [edit, setEdit] = useState(null);
  const [sel, setSel] = useState([]);
  const ref = useRef();
  const load = () => api.get("/admin/media", { params: { q, category: cat } }).then((r) => setItems(r.data.items));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { load(); }, [q, cat]);
  const upload = async (files) => {
    if (!files?.length) return;
    setBusy(true);
    const fd = new FormData();
    [...files].forEach((f) => fd.append("files", f));
    try { const { data } = await api.post("/admin/media", fd); toast.success(`Uploadovano: ${data.length}`); load(); }
    catch (e) { toast.error(errMsg(e)); } finally { setBusy(false); }
  };
  const click = (m) => {
    if (!onPick) return setEdit(m);
    if (!multi) return onPick(m);
    setSel((s) => (s.find((x) => x.id === m.id) ? s.filter((x) => x.id !== m.id) : [...s, m]));
  };
  return (
    <div data-testid="media-library">
      <div onDragOver={(e) => { e.preventDefault(); setDrag(true); }} onDragLeave={() => setDrag(false)}
        onDrop={(e) => { e.preventDefault(); setDrag(false); upload(e.dataTransfer.files); }} onClick={() => ref.current.click()}
        className={`border-2 border-dashed rounded-md p-6 text-center cursor-pointer transition-colors ${drag ? "border-ccn-teal bg-teal-50" : "border-slate-300 bg-white"}`} data-testid="media-dropzone">
        <Upload className="w-6 h-6 mx-auto text-slate-400" />
        <p className="text-sm mt-2">{busy ? "Obrada i optimizacija…" : "Prevucite slike ovdje ili kliknite (JPG, PNG, WebP, AVIF – max 15 MB)"}</p>
        <input ref={ref} type="file" multiple accept="image/jpeg,image/png,image/webp,image/avif" className="hidden" onChange={(e) => upload(e.target.files)} data-testid="media-file-input" />
      </div>
      <div className="flex gap-2 my-4">
        <Input placeholder="Pretraži (ALT, opis, autor…)" value={q} onChange={(e) => setQ(e.target.value)} data-testid="media-search" />
        <Input placeholder="Kategorija" value={cat} onChange={(e) => setCat(e.target.value)} className="w-40" data-testid="media-category-filter" />
        {multi && <Button onClick={() => onPick(sel)} disabled={!sel.length} className="bg-ccn-navy" data-testid="media-pick-confirm"><Check className="w-4 h-4 mr-1" />Dodaj ({sel.length})</Button>}
      </div>
      <div className="grid grid-cols-3 sm:grid-cols-4 lg:grid-cols-6 gap-2">
        {items.map((m) => (
          <button key={m.id} onClick={() => click(m)} data-testid={`media-item-${m.id}`}
            className={`relative aspect-square overflow-hidden rounded-sm border-2 ${sel.find((x) => x.id === m.id) ? "border-ccn-teal" : "border-transparent"}`}>
            <img src={mediaUrl(m.thumb)} alt={m.alt} loading="lazy" className="w-full h-full object-cover" />
            {!m.alt && <span className="absolute bottom-1 left-1 text-[9px] bg-amber-400 px-1 rounded-sm">bez ALT</span>}
          </button>
        ))}
      </div>
      <Dialog open={!!edit} onOpenChange={() => setEdit(null)}>
        <DialogContent className="max-w-3xl"><DialogTitle>Detalji fotografije</DialogTitle>
          {edit && <MetaEditor m={edit} onClose={() => setEdit(null)} onSaved={(d) => { load(); if (d) setEdit(d); }} />}
        </DialogContent>
      </Dialog>
    </div>
  );
}

export function MediaPicker({ open, onClose, onPick, multi }) {
  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-5xl max-h-[90vh] overflow-y-auto" data-testid="media-picker">
        <DialogTitle>Odaberite fotografiju{multi ? "e" : ""}</DialogTitle>
        <MediaLibrary multi={multi} onPick={(m) => { onPick(m); onClose(); }} />
      </DialogContent>
    </Dialog>
  );
}

export default function MediaPage() {
  return (
    <div>
      <h1 className="font-serif-news text-2xl md:text-3xl font-black mb-6">Medijska biblioteka</h1>
      <MediaLibrary />
    </div>
  );
}
