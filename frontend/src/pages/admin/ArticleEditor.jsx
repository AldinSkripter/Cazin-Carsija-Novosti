import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";
import { Save, Send, CheckCircle2, XCircle, Globe, CalendarClock, Undo2, Archive, Copy, Eye, History, Sparkles, X, ImagePlus, Trash2 } from "lucide-react";
import { api, errMsg, mediaUrl, fmtDate, STATUS_LABELS, STATUS_COLORS } from "../../lib/api";
import { useAuth } from "../../lib/auth";
import { RichEditor } from "./RichEditor";
import { MediaPicker, snap } from "./Media";
import { ArticleView } from "../../components/public/ArticleView";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Textarea } from "../../components/ui/textarea";
import { Switch } from "../../components/ui/switch";
import { Dialog, DialogContent, DialogTitle } from "../../components/ui/dialog";

export const toLocal = (iso) => { if (!iso) return ""; const d = new Date(iso); return new Date(d - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16); };
export const fromLocal = (v) => (v ? new Date(v).toISOString() : null);

const EMPTY = { title: "", subtitle: "", summary: "", body: "", slug: "", category_id: "", category_ids: [], tags: [], author_ids: [], source: "", source_author: "",
  featured_image: null, gallery: [], video_urls: [], seo_title: "", seo_description: "", canonical_url: "", social_image: "", publish_at: null,
  is_breaking: false, is_pinned: false, is_exclusive: false, is_sponsored: false, allow_comments: true, show_views: true, status: "draft" };

const Box = ({ title, children }) => <div className="bg-white border rounded-md p-4"><h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3">{title}</h3><div className="grid gap-2">{children}</div></div>;

const AI_ACTIONS = [["titles", "Naslovi"], ["subtitle", "Podnaslov"], ["summary", "Sažetak"], ["proofread", "Pravopis"], ["tags", "Oznake i kategorija"], ["seo", "SEO opis"], ["facebook", "Facebook objava"]];

function AiPanel({ a, setField }) {
  const [res, setRes] = useState(null);
  const [busy, setBusy] = useState("");
  const run = async (action) => {
    setBusy(action);
    try {
      const { data } = await api.post(`/admin/ai/${action}`, { text: `${a.title}\n${a.subtitle}\n${a.body}`, article_id: a.id });
      setRes({ action, text: data.result });
    } catch (e) { toast.error(errMsg(e)); } finally { setBusy(""); }
  };
  const apply = { subtitle: "subtitle", summary: "summary", seo: "seo_description" }[res?.action];
  return (
    <Box title="AI asistent (Claude)">
      <div className="flex flex-wrap gap-1">{AI_ACTIONS.map(([k, l]) => <Button key={k} size="sm" variant="outline" disabled={!!busy} onClick={() => run(k)} data-testid={`ai-${k}`}><Sparkles className="w-3 h-3 mr-1" />{busy === k ? "…" : l}</Button>)}</div>
      {res && (
        <div className="bg-slate-50 border rounded-sm p-3 text-sm" data-testid="ai-result">
          <p className="whitespace-pre-line">{res.text}</p>
          <p className="text-[11px] text-amber-700 mt-2">AI prijedlog – provjerite činjenice prije korištenja. AI ne objavljuje ništa samostalno.</p>
          <div className="flex gap-2 mt-2">
            {apply && <Button size="sm" onClick={() => { setField(apply, res.text); setRes(null); }} data-testid="ai-apply">Primijeni</Button>}
            {res.action === "titles" && res.text.split("\n").filter(Boolean).slice(0, 5).map((t) => <Button key={t} size="sm" variant="outline" className="text-left h-auto whitespace-normal" onClick={() => setField("title", t.replace(/^[-•\d.\s]+/, ""))}>{t.slice(0, 40)}…</Button>)}
            <Button size="sm" variant="ghost" onClick={() => setRes(null)}>Zatvori</Button>
          </div>
        </div>
      )}
    </Box>
  );
}

function Actions({ a, can, act, save, dirty }) {
  const p = (x) => can(x);
  const st = a.status;
  return (
    <Box title="Objava">
      <div className="flex items-center justify-between"><span className={`text-xs px-2 py-1 rounded-full font-semibold ${STATUS_COLORS[st]}`} data-testid="editor-status">{STATUS_LABELS[st]}</span>{dirty && <span className="text-xs text-amber-600">nesačuvane izmjene</span>}</div>
      {a.rejection_reason && st === "rejected" && <p className="text-xs bg-red-50 text-red-700 p-2 rounded-sm" data-testid="rejection-reason">Obrazloženje: {a.rejection_reason}</p>}
      {a.can_edit !== false && <Button onClick={() => save(false)} className="bg-ccn-navy" data-testid="editor-save"><Save className="w-4 h-4 mr-1" />Sačuvaj</Button>}
      {a.id && ["draft", "rejected"].includes(st) && <Button variant="outline" onClick={() => act("submit")} data-testid="editor-submit-review"><Send className="w-4 h-4 mr-1" />Pošalji na pregled</Button>}
      {a.id && p("articles.approve") && ["review", "scheduled"].includes(st) && <Button variant="outline" onClick={() => act("approve")} data-testid="editor-approve"><CheckCircle2 className="w-4 h-4 mr-1" />Odobri</Button>}
      {a.id && p("articles.approve") && ["review", "approved", "scheduled"].includes(st) && <Button variant="outline" className="text-ccn-red" onClick={() => { const r = window.prompt("Obrazloženje odbijanja:"); if (r) act("reject", { reason: r }); }} data-testid="editor-reject"><XCircle className="w-4 h-4 mr-1" />Odbij</Button>}
      {a.id && p("articles.publish") && st !== "published" && <Button className="bg-ccn-teal text-ccn-navy hover:bg-ccn-gold" onClick={() => act("publish")} data-testid="editor-publish"><Globe className="w-4 h-4 mr-1" />{a.publish_at && a.publish_at > new Date().toISOString() ? "Zakaži objavu" : "Objavi odmah"}</Button>}
      {a.id && p("articles.publish") && st === "published" && <Button variant="outline" onClick={() => act("unpublish")} data-testid="editor-unpublish"><Undo2 className="w-4 h-4 mr-1" />Povuci objavu</Button>}
      {a.id && p("articles.publish") && st !== "archived" && <Button variant="ghost" size="sm" onClick={() => act("archive")} data-testid="editor-archive"><Archive className="w-4 h-4 mr-1" />Arhiviraj</Button>}
      {!p("articles.publish") && <p className="text-[11px] text-slate-500">Nemate dozvolu za objavu – pošaljite članak uredniku na pregled.</p>}
    </Box>
  );
}

export default function ArticleEditor() {
  const { id } = useParams();
  const nav = useNavigate();
  const { can, user } = useAuth();
  const [a, setA] = useState(id === "novi" ? { ...EMPTY } : null);
  const [cats, setCats] = useState([]);
  const [people, setPeople] = useState([]);
  const [dirty, setDirty] = useState(false);
  const [pick, setPick] = useState(null);
  const [preview, setPreview] = useState(false);
  const [versions, setVersions] = useState(null);
  const [dups, setDups] = useState([]);
  const [tagText, setTagText] = useState("");
  const aRef = useRef(a);
  aRef.current = a;
  const savingRef = useRef(null);
  useEffect(() => {
    api.get("/public/categories").then((r) => setCats(r.data));
    api.get("/admin/users/directory").then((r) => setPeople(r.data));
  }, []);
  useEffect(() => {
    if (id !== "novi") api.get(`/admin/articles/${id}`).then((r) => { setA(r.data); setTagText(r.data.tags.join(", ")); }).catch((e) => toast.error(errMsg(e)));
  }, [id]);
  const setField = (k, v) => { setA((x) => ({ ...x, [k]: v })); setDirty(true); };
  const payload = (x) => ({ ...x, category_id: x.category_id || null, tags: tagText.split(",").map((t) => t.trim()).filter(Boolean) });
  const save = useCallback(async (autosave) => {
    if (savingRef.current) return savingRef.current;
    savingRef.current = doSave(autosave).finally(() => { savingRef.current = null; });
    return savingRef.current;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nav, tagText]);
  const doSave = async (autosave) => {
    const cur = aRef.current;
    if (!cur.title.trim()) { if (!autosave) toast.error("Unesite naslov"); return null; }
    try {
      if (!cur.id) {
        const { data } = await api.post("/admin/articles", payload(cur));
        setDirty(false); toast.success("Nacrt kreiran"); nav(`/admin/clanci/${data.id}`, { replace: true }); return data;
      }
      const { data } = await api.put(`/admin/articles/${cur.id}`, payload(cur), { params: { autosave } });
      setDirty(false);
      setA((x) => ({ ...x, slug: data.slug, updated_at: data.updated_at }));
      if (!autosave) toast.success("Sačuvano"); else toast.message("Automatski sačuvano", { duration: 1500 });
      return data;
    } catch (e) { if (!autosave) toast.error(errMsg(e)); return null; }
  };
  useEffect(() => {
    const t = setInterval(() => { if (dirty && aRef.current?.id && aRef.current.can_edit !== false) save(true); }, 30000);
    return () => clearInterval(t);
  }, [dirty, save]);
  const act = async (action, extra = {}) => {
    if (savingRef.current) await savingRef.current;
    if (dirty && a.can_edit !== false) { const ok = await save(false); if (!ok) return; }
    try { const { data } = await api.post(`/admin/articles/${a.id}/transition`, { action, ...extra }); setA((x) => ({ ...x, ...data })); toast.success(`Status: ${STATUS_LABELS[data.status]}`); }
    catch (e) { toast.error(errMsg(e)); }
  };
  const checkDups = () => { if (a.title.length > 10) api.get("/admin/articles/duplicates", { params: { title: a.title, exclude: a.id || "" } }).then((r) => setDups(r.data)).catch(() => {}); };
  const openVersions = () => api.get(`/admin/articles/${a.id}/versions`).then((r) => setVersions(r.data));
  const restore = async (v) => { if (!window.confirm(`Vratiti verziju ${v.version}?`)) return; await api.post(`/admin/articles/${a.id}/versions/${v.id}/restore`); toast.success("Verzija vraćena"); window.location.reload(); };
  const duplicate = async () => { const { data } = await api.post(`/admin/articles/${a.id}/duplicate`); toast.success("Kopija kreirana"); nav(`/admin/clanci/${data.id}`); };
  if (!a) return <p>Učitavanje…</p>;
  const ro = a.can_edit === false;
  const cat = cats.find((c) => c.id === a.category_id);
  return (
    <div data-testid="article-editor">
      <div className="flex flex-wrap gap-2 mb-4 items-center">
        <h1 className="font-serif-news text-2xl font-black flex-1">{a.id ? "Uređivanje članka" : "Novi članak"}</h1>
        <Button variant="outline" size="sm" onClick={() => setPreview(true)} data-testid="editor-preview"><Eye className="w-4 h-4 mr-1" />Pregled</Button>
        {a.id && <Button variant="outline" size="sm" onClick={openVersions} data-testid="editor-versions"><History className="w-4 h-4 mr-1" />Verzije</Button>}
        {a.id && can("articles.create") && <Button variant="outline" size="sm" onClick={duplicate} data-testid="editor-duplicate"><Copy className="w-4 h-4 mr-1" />Dupliraj</Button>}
        {a.status === "published" && <a href={`/vijesti/${a.slug}`} target="_blank" rel="noreferrer"><Button variant="outline" size="sm" data-testid="editor-view-live"><Globe className="w-4 h-4 mr-1" />Na portalu</Button></a>}
      </div>
      {ro && <p className="mb-4 bg-amber-50 border border-amber-200 text-amber-900 text-sm px-4 py-2 rounded-sm" data-testid="editor-readonly">Samo pregled – nemate dozvolu za uređivanje ovog članka u trenutnom statusu.</p>}
      <div className="grid xl:grid-cols-12 gap-5">
        <fieldset disabled={ro} className="xl:col-span-8 grid gap-3 content-start">
          <Input value={a.title} onChange={(e) => setField("title", e.target.value)} onBlur={checkDups} placeholder="Naslov vijesti" className="text-xl font-bold h-12 bg-white" data-testid="editor-title" />
          {dups.length > 0 && <div className="text-xs bg-amber-50 border border-amber-200 p-2 rounded-sm" data-testid="editor-duplicates">Mogući duplikati: {dups.map((d) => <a key={d.id} href={`/admin/clanci/${d.id}`} className="underline mr-2">{d.title} ({Math.round(d.score * 100)}%)</a>)}</div>}
          <Input value={a.subtitle} onChange={(e) => setField("subtitle", e.target.value)} placeholder="Podnaslov" className="bg-white" data-testid="editor-subtitle" />
          <Textarea value={a.summary} onChange={(e) => setField("summary", e.target.value)} placeholder="Kratki sažetak (prikazuje se na naslovnoj i u pretrazi)" rows={2} className="bg-white" data-testid="editor-summary" />
          <RichEditor value={a.body} onChange={(v) => setField("body", v)} />
          <Box title="Foto galerija">
            <div className="flex flex-wrap gap-2" data-testid="editor-gallery">
              {a.gallery.map((g, i) => (
                <div key={g.id + i} className="relative w-24 h-24"><img src={mediaUrl(g.thumb)} alt="" className="w-full h-full object-cover rounded-sm" />
                  <button type="button" onClick={() => setField("gallery", a.gallery.filter((_, j) => j !== i))} className="absolute top-1 right-1 bg-white rounded-full p-0.5" aria-label="Ukloni"><X className="w-3 h-3" /></button></div>
              ))}
              <button type="button" onClick={() => setPick("gallery")} className="w-24 h-24 border-2 border-dashed rounded-sm flex items-center justify-center text-slate-400" data-testid="editor-gallery-add"><ImagePlus /></button>
            </div>
          </Box>
          <Box title="Video prilozi (YouTube linkovi, jedan po redu)">
            <Textarea rows={2} value={a.video_urls.join("\n")} onChange={(e) => setField("video_urls", e.target.value.split("\n").map((s) => s.trim()).filter(Boolean))} placeholder="https://www.youtube.com/watch?v=…" data-testid="editor-videos" />
          </Box>
          <Box title="SEO i društvene mreže">
            <Input value={a.seo_title} onChange={(e) => setField("seo_title", e.target.value)} placeholder="SEO naslov (prazno = naslov)" data-testid="editor-seo-title" />
            <Textarea rows={2} value={a.seo_description} onChange={(e) => setField("seo_description", e.target.value)} placeholder="Meta opis (do 155 znakova)" data-testid="editor-seo-description" />
            <p className="text-[11px] text-slate-500">{a.seo_description.length}/155</p>
            <Input value={a.slug} onChange={(e) => setField("slug", e.target.value)} placeholder="URL slug (automatski iz naslova)" data-testid="editor-slug" />
            <Input value={a.canonical_url} onChange={(e) => setField("canonical_url", e.target.value)} placeholder="Canonical URL (opcionalno)" data-testid="editor-canonical" />
            <Input value={a.social_image} onChange={(e) => setField("social_image", e.target.value)} placeholder="Društvena fotografija URL (prazno = naslovna)" data-testid="editor-social-image" />
          </Box>
        </fieldset>
        <div className="xl:col-span-4 grid gap-4 content-start">
          <Actions a={a} can={can} act={act} save={save} dirty={dirty} />
          <fieldset disabled={ro} className="grid gap-4">
            <Box title="Raspored objave">
              <Input type="datetime-local" value={toLocal(a.publish_at)} onChange={(e) => setField("publish_at", fromLocal(e.target.value))} data-testid="editor-publish-at" />
              <p className="text-[11px] text-slate-500">Budući datum + „Zakaži objavu“ = automatska objava u zadano vrijeme.</p>
              {a.published_at && <p className="text-xs">Objavljeno: {fmtDate(a.published_at)}</p>}
            </Box>
            <Box title="Naslovna fotografija">
              {a.featured_image ? (
                <div className="relative"><img src={mediaUrl(a.featured_image.medium)} alt="" className="rounded-sm w-full" data-testid="editor-featured-preview" />
                  <button type="button" onClick={() => setField("featured_image", null)} className="absolute top-2 right-2 bg-white rounded-full p-1" aria-label="Ukloni"><Trash2 className="w-4 h-4 text-ccn-red" /></button>
                  <p className="text-[11px] text-slate-500 mt-1">ALT: {a.featured_image.alt || "— (dodajte u biblioteci)"}</p></div>
              ) : <Button type="button" variant="outline" onClick={() => setPick("featured")} data-testid="editor-featured-pick"><ImagePlus className="w-4 h-4 mr-1" />Odaberi fotografiju</Button>}
            </Box>
            <Box title="Kategorija i oznake">
              <select value={a.category_id || ""} onChange={(e) => setField("category_id", e.target.value)} className="border rounded-sm px-3 py-2 text-sm" data-testid="editor-category">
                <option value="">— Glavna kategorija —</option>{cats.map((c) => <option key={c.id} value={c.id}>{c.parent_id ? "— " : ""}{c.name}</option>)}
              </select>
              <details className="text-sm"><summary className="cursor-pointer text-slate-600">Dodatne kategorije ({a.category_ids.length})</summary>
                <div className="max-h-40 overflow-y-auto mt-2 grid gap-1">{cats.filter((c) => c.id !== a.category_id).map((c) => (
                  <label key={c.id} className="flex gap-2 text-xs"><input type="checkbox" checked={a.category_ids.includes(c.id)} onChange={(e) => setField("category_ids", e.target.checked ? [...a.category_ids, c.id] : a.category_ids.filter((x) => x !== c.id))} />{c.name}</label>))}
                </div></details>
              <Input value={tagText} onChange={(e) => { setTagText(e.target.value); setDirty(true); }} placeholder="Oznake, odvojene zarezom" data-testid="editor-tags" />
              {cat && <p className="text-[11px] text-slate-500">URL: /vijesti/{a.slug || "…"}</p>}
            </Box>
            <Box title="Autori i izvor">
              <div className="max-h-32 overflow-y-auto grid gap-1" data-testid="editor-authors">{people.map((u) => (
                <label key={u.id} className="flex gap-2 text-xs"><input type="checkbox" checked={a.author_ids.includes(u.id) || (!a.author_ids.length && u.id === user.id)}
                  onChange={(e) => { const base = a.author_ids.length ? a.author_ids : [user.id]; setField("author_ids", e.target.checked ? [...base, u.id] : base.filter((x) => x !== u.id)); }} />{u.name}</label>))}
              </div>
              <Input value={a.source} onChange={(e) => setField("source", e.target.value)} placeholder="Izvor informacije" data-testid="editor-source" />
              <Input value={a.source_author} onChange={(e) => setField("source_author", e.target.value)} placeholder="Autor izvora" data-testid="editor-source-author" />
            </Box>
            <Box title="Isticanje">
              {[["is_breaking", "Breaking News (crvena traka)"], ["is_pinned", "Fiksiraj na vrhu naslovne"], ["is_exclusive", "Ekskluzivno"], ["is_sponsored", "Sponzorisani sadržaj"], ["allow_comments", "Dozvoli komentare"], ["show_views", "Prikaži broj pregleda"]].map(([k, l]) => (
                <label key={k} className="flex items-center justify-between text-sm">{l}<Switch checked={!!a[k]} onCheckedChange={(v) => setField(k, v)} data-testid={`editor-${k}`} /></label>
              ))}
            </Box>
          </fieldset>
          {can("ai.use") && !ro && <AiPanel a={a} setField={setField} />}
        </div>
      </div>
      <MediaPicker open={!!pick} multi={pick === "gallery"} onClose={() => setPick(null)}
        onPick={(m) => (pick === "gallery" ? setField("gallery", [...a.gallery, ...m.map(snap)]) : setField("featured_image", snap(m)))} />
      <Dialog open={preview} onOpenChange={setPreview}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto" data-testid="preview-dialog">
          <DialogTitle>Pregled članka prije objave</DialogTitle>
          <ArticleView a={{ ...a, category: cat, authors: people.filter((u) => (a.author_ids.length ? a.author_ids : [user.id]).includes(u.id)), tags: tagText.split(",").map((t) => t.trim()).filter(Boolean) }} preview />
        </DialogContent>
      </Dialog>
      <Dialog open={!!versions} onOpenChange={() => setVersions(null)}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto" data-testid="versions-dialog">
          <DialogTitle>Historija verzija</DialogTitle>
          {versions?.map((v) => (
            <div key={v.id} className="flex items-center justify-between py-2 border-b text-sm">
              <span><strong>v{v.version}</strong> · {v.user_name} · {fmtDate(v.created_at)} · <span className="text-slate-500">{v.note}</span></span>
              {!ro && <Button size="sm" variant="outline" onClick={() => restore(v)} data-testid={`restore-version-${v.version}`}>Vrati</Button>}
            </div>
          ))}
        </DialogContent>
      </Dialog>
    </div>
  );
}
