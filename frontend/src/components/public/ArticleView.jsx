import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Clock, Eye, RefreshCw, Flag, BookOpen } from "lucide-react";
import { toast } from "sonner";
import { Share, ShareBottom, ReuseBox } from "./ShareReuse";
import { api, errMsg, fmtDate, mediaUrl, strip } from "../../lib/api";
import { ArticleCard, CatPill } from "./ArticleCard";
import { AdSlot } from "./AdSlot";
import { Dialog, DialogContent, DialogTitle } from "../ui/dialog";

function youtubeEmbed(url) {
  const m = url.match(/(?:youtu\.be\/|v=|embed\/|shorts\/)([\w-]{11})/);
  return m ? `https://www.youtube-nocookie.com/embed/${m[1]}` : null;
}


function Gallery({ items }) {
  const [open, setOpen] = useState(null);
  if (!items?.length) return null;
  return (
    <section className="my-8" data-testid="article-gallery">
      <h2 className="font-bold text-lg mb-3">Foto galerija ({items.length})</h2>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
        {items.map((g, i) => (
          <button key={g.id + i} onClick={() => setOpen(i)} className="aspect-[4/3] overflow-hidden rounded-sm" data-testid={`gallery-item-${i}`}>
            <img src={mediaUrl(g.thumb || g.medium)} alt={g.alt || ""} loading="lazy" className="w-full h-full object-cover hover:scale-105 transition-transform" />
          </button>
        ))}
      </div>
      <Dialog open={open !== null} onOpenChange={() => setOpen(null)}>
        <DialogContent className="max-w-5xl bg-black border-0 p-2">
          <DialogTitle className="sr-only">Galerija</DialogTitle>
          {open !== null && (
            <div>
              <img src={mediaUrl(items[open].large)} alt={items[open].alt || ""} className="w-full max-h-[80vh] object-contain" />
              <div className="flex justify-between text-white/70 text-xs p-2">
                <span>{items[open].caption || items[open].alt} {items[open].credit && `· Foto: ${items[open].credit}`}</span>
                <span className="flex gap-3">
                  <button onClick={() => setOpen((open - 1 + items.length) % items.length)} data-testid="gallery-prev">‹ Prethodna</button>
                  <button onClick={() => setOpen((open + 1) % items.length)} data-testid="gallery-next">Sljedeća ›</button>
                </span>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </section>
  );
}

function Comments({ a }) {
  const [list, setList] = useState([]);
  const [form, setForm] = useState({ name: "", email: "", content: "", website: "" });
  useEffect(() => { api.get(`/public/articles/${a.id}/comments`).then((r) => setList(r.data)).catch(() => {}); }, [a.id]);
  const submit = async (e) => {
    e.preventDefault();
    try {
      const { data } = await api.post(`/public/articles/${a.id}/comments`, form);
      toast.success(data.status === "approved" ? "Komentar objavljen" : "Komentar je poslan i čeka odobrenje moderatora");
      setForm({ name: "", email: "", content: "", website: "" });
    } catch (err) { toast.error(errMsg(err)); }
  };
  const report = (id) => api.post(`/public/comments/${id}/report`).then(() => toast.success("Prijava poslana moderatorima"));
  return (
    <section className="mt-10 pt-8 border-t border-ccn-mist" data-testid="comments-section">
      <h2 className="font-bold text-xl mb-4">Komentari ({list.length})</h2>
      {list.map((c) => (
        <div key={c.id} className="py-3 border-b border-ccn-mist" data-testid={`comment-${c.id}`}>
          <p className="text-sm"><strong>{c.name}</strong> <span className="text-slate-400 text-xs">{fmtDate(c.created_at)}</span></p>
          <p className="mt-1 text-[15px] whitespace-pre-line">{c.content}</p>
          <button onClick={() => report(c.id)} className="text-xs text-slate-400 hover:text-ccn-red mt-1 flex items-center gap-1" data-testid={`comment-report-${c.id}`}><Flag className="w-3 h-3" />Prijavi</button>
        </div>
      ))}
      <form onSubmit={submit} className="mt-6 grid gap-3 bg-white p-5 rounded-md border border-ccn-mist" data-testid="comment-form">
        <div className="grid sm:grid-cols-2 gap-3">
          <input required placeholder="Ime *" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="border rounded-sm px-3 py-2 text-sm" data-testid="comment-name" />
          <input type="email" placeholder="E-mail (neće biti objavljen)" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} className="border rounded-sm px-3 py-2 text-sm" data-testid="comment-email" />
        </div>
        <input tabIndex={-1} autoComplete="off" className="hidden" value={form.website} onChange={(e) => setForm({ ...form, website: e.target.value })} aria-hidden="true" />
        <textarea required rows={4} placeholder="Vaš komentar…" value={form.content} onChange={(e) => setForm({ ...form, content: e.target.value })} className="border rounded-sm px-3 py-2 text-sm" data-testid="comment-content" />
        <p className="text-xs text-slate-500">Komentari se objavljuju nakon odobrenja. Zabranjen je govor mržnje i vrijeđanje.</p>
        <button className="justify-self-start bg-ccn-navy text-white px-5 py-2 rounded-sm text-sm font-semibold hover:bg-ccn-tealdark" data-testid="comment-submit">Pošalji komentar</button>
      </form>
    </section>
  );
}

function ReadProgress() {
  const [p, setP] = useState(0);
  useEffect(() => {
    const on = () => { const h = document.documentElement; setP(Math.min(100, (h.scrollTop / Math.max(1, h.scrollHeight - h.clientHeight)) * 100)); };
    window.addEventListener("scroll", on, { passive: true });
    return () => window.removeEventListener("scroll", on);
  }, []);
  return <div className="read-progress" style={{ width: `${p}%` }} aria-hidden="true" data-testid="read-progress" />;
}

function AuthorCard({ authors }) {
  if (!authors?.length) return null;
  return (
    <div className="mt-10 grid gap-3" data-testid="author-card">
      {authors.map((u) => (
        <Link key={u.id} to={`/autor/${u.slug}`} className="flex gap-4 items-center bg-white border border-ccn-mist rounded-lg p-5 hover:border-ccn-teal transition-colors">
          <span className="w-14 h-14 rounded-full bg-ccn-navy text-ccn-gold font-serif-news font-black text-xl flex items-center justify-center shrink-0">{u.name?.[0]}</span>
          <span><span className="text-[11px] uppercase tracking-widest text-slate-500">Autor</span><span className="block font-bold">{u.name}</span>{u.bio && <span className="block text-sm text-slate-600 line-clamp-2">{u.bio}</span>}</span>
        </Link>
      ))}
    </div>
  );
}

export function ArticleView({ a, preview = false }) {
  const mins = Math.max(1, Math.round(strip(a.body).split(/\s+/).length / 200));
  const img = a.featured_image;
  const videos = (a.video_urls || []).map(youtubeEmbed).filter(Boolean);
  const half = Math.floor((a.body || "").length / 2);
  const cut = (a.body || "").indexOf("</p>", half);
  const [b1, b2] = cut > 0 ? [a.body.slice(0, cut + 4), a.body.slice(cut + 4)] : [a.body || "", ""];
  return (
    <article className="max-w-3xl" data-testid="article-view">
      {!preview && <ReadProgress />}
      <nav aria-label="Breadcrumb" className="text-xs text-slate-500 mb-4" data-testid="breadcrumbs">
        <Link to="/" className="hover:text-ccn-tealdark">Naslovna</Link>
        {a.category && <> / <Link to={`/kategorija/${a.category.slug}`} className="hover:text-ccn-tealdark">{a.category.name}</Link></>}
      </nav>
      <div className="flex flex-wrap gap-2 mb-4">
        {a.category && <Link to={`/kategorija/${a.category.slug}`}><CatPill c={a.category} className="!text-xs !px-2.5 !py-1" /></Link>}
        {a.is_exclusive && <span className="bg-ccn-gold text-ccn-navy text-xs font-bold uppercase px-2 py-1 rounded-sm">Ekskluzivno</span>}
        {a.is_sponsored && <span className="bg-slate-200 text-slate-700 text-xs font-bold uppercase px-2 py-1 rounded-sm" data-testid="sponsored-label">Sponzorisani sadržaj</span>}
      </div>
      <h1 className="font-serif-news text-[32px] sm:text-[42px] lg:text-[50px] font-black leading-[1.12] tracking-[-0.01em]" data-testid="article-title">{a.title}</h1>
      {a.subtitle && <p className="mt-5 text-lg md:text-[22px] text-slate-600 leading-relaxed font-light" data-testid="article-subtitle">{a.subtitle}</p>}
      <div className="mt-6 flex flex-wrap items-center justify-between gap-4 py-4 border-y border-ccn-mist">
        <div className="text-sm flex items-center gap-3">
          <span className="w-10 h-10 rounded-full bg-ccn-navy text-ccn-gold font-bold flex items-center justify-center shrink-0">{a.authors?.[0]?.name?.[0] || "R"}</span>
          <div>
          <p className="font-semibold" data-testid="article-authors">
            {(a.authors || []).map((u, i) => <span key={u.id}>{i > 0 && ", "}<Link to={`/autor/${u.slug}`} className="hover:text-ccn-tealdark">{u.name}</Link></span>)}
            {!a.authors?.length && "Redakcija"}
          </p>
          <p className="text-slate-500 text-xs flex flex-wrap gap-3 mt-1">
            <span className="flex items-center gap-1"><Clock className="w-3 h-3" />{fmtDate(a.published_at || a.updated_at)}</span>
            {a.published_at && a.updated_at && a.updated_at.slice(0, 16) > a.published_at.slice(0, 16) && <span className="flex items-center gap-1" data-testid="article-updated"><RefreshCw className="w-3 h-3" />Ažurirano {fmtDate(a.updated_at)}</span>}
            {a.views !== undefined && <span className="flex items-center gap-1" data-testid="article-views"><Eye className="w-3 h-3" />{a.views} pregleda</span>}
            <span className="flex items-center gap-1"><BookOpen className="w-3 h-3" />{mins} min čitanja</span>
          </p>
          </div>
        </div>
        {!preview && <Share a={a} />}
      </div>
      {img && (
        <figure className="mt-7 -mx-4 sm:mx-0">
          <img src={mediaUrl(img.large)} alt={img.alt || a.title} className="w-full max-h-[70vh] object-cover sm:rounded-lg" data-testid="article-featured-image" />
          {(img.caption || img.credit) && <figcaption className="text-xs text-slate-500 mt-2 px-4 sm:px-0">{img.caption} {img.credit && <span className="italic">Foto: {img.credit}</span>}</figcaption>}
        </figure>
      )}
      {a.summary && <p className="mt-8 font-semibold text-[19px] leading-relaxed bg-ccn-mist/50 border-l-4 border-ccn-teal rounded-r-lg px-5 py-4">{a.summary}</p>}
      <div className="article-body drop-cap mt-8" dangerouslySetInnerHTML={{ __html: b1 }} data-testid="article-body" />
      {!preview && b2 && <AdSlot position="in_article" className="my-6" />}
      {b2 && <div className="article-body" dangerouslySetInnerHTML={{ __html: b2 }} />}
      {videos.map((v) => <iframe key={v} src={v} title="Video" className="w-full aspect-video rounded-sm my-6" allowFullScreen loading="lazy" data-testid="article-video" />)}
      <Gallery items={a.gallery} />
      {(a.source || a.source_author) && <p className="text-sm text-slate-500 mt-6" data-testid="article-source">Izvor: {a.source}{a.source_author && ` (${a.source_author})`}</p>}
      {a.tags?.length > 0 && (
        <div className="flex flex-wrap gap-2 mt-6" data-testid="article-tags">
          {a.tags.map((t) => <Link key={t} to={`/tema/${encodeURIComponent(t)}`} className="text-sm px-3 py-1 bg-ccn-mist rounded-full hover:bg-ccn-teal">#{t}</Link>)}
        </div>
      )}
      {!preview && <ShareBottom a={a} />}
      {!preview && <ReuseBox a={a} />}
      {!preview && <AuthorCard authors={a.authors} />}
      {!preview && <AdSlot position="below_article" className="mt-8" />}
      {!preview && a.comments_open && <Comments a={a} />}
      {!preview && a.related?.length > 0 && (
        <section className="mt-12" data-testid="related-articles">
          <h2 className="font-serif-news font-black text-2xl mb-6 flex items-center gap-3"><span className="w-1.5 h-7 rounded-full bg-ccn-gold" />Povezane vijesti</h2>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-5">{a.related.slice(0, 6).map((r) => <ArticleCard key={r.id} a={r} />)}</div>
        </section>
      )}
    </article>
  );
}
