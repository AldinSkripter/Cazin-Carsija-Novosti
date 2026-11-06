import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Clock, Eye, RefreshCw, Facebook, Twitter, Link2, MessageCircle, Flag } from "lucide-react";
import { toast } from "sonner";
import { api, errMsg, fmtDate, mediaUrl, shareUrl } from "../../lib/api";
import { ArticleCard } from "./ArticleCard";
import { AdSlot } from "./AdSlot";
import { Dialog, DialogContent, DialogTitle } from "../ui/dialog";

function youtubeEmbed(url) {
  const m = url.match(/(?:youtu\.be\/|v=|embed\/|shorts\/)([\w-]{11})/);
  return m ? `https://www.youtube-nocookie.com/embed/${m[1]}` : null;
}

function Share({ a }) {
  const u = encodeURIComponent(shareUrl(a));
  const t = encodeURIComponent(a.title);
  const links = [
    ["facebook", Facebook, `https://www.facebook.com/sharer/sharer.php?u=${u}`],
    ["x", Twitter, `https://twitter.com/intent/tweet?url=${u}&text=${t}`],
    ["whatsapp", MessageCircle, `https://wa.me/?text=${t}%20${u}`],
    ["viber", MessageCircle, `viber://forward?text=${t}%20${u}`],
  ];
  return (
    <div className="flex gap-2" data-testid="share-buttons">
      {links.map(([k, I, href]) => (
        <a key={k} href={href} target="_blank" rel="noopener noreferrer" aria-label={`Podijeli na ${k}`} data-testid={`share-${k}`}
          className="w-9 h-9 rounded-full bg-ccn-navy text-white flex items-center justify-center hover:bg-ccn-teal hover:text-ccn-navy transition-colors">
          <I className="w-4 h-4" />
        </a>
      ))}
      <button onClick={() => { navigator.clipboard?.writeText(window.location.href); toast.success("Link kopiran"); }} aria-label="Kopiraj link" data-testid="share-copy"
        className="w-9 h-9 rounded-full bg-ccn-mist flex items-center justify-center hover:bg-ccn-gold transition-colors"><Link2 className="w-4 h-4" /></button>
    </div>
  );
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

export function ArticleView({ a, preview = false }) {
  const img = a.featured_image;
  const videos = (a.video_urls || []).map(youtubeEmbed).filter(Boolean);
  const half = Math.floor((a.body || "").length / 2);
  const cut = (a.body || "").indexOf("</p>", half);
  const [b1, b2] = cut > 0 ? [a.body.slice(0, cut + 4), a.body.slice(cut + 4)] : [a.body || "", ""];
  return (
    <article className="max-w-3xl" data-testid="article-view">
      <nav aria-label="Breadcrumb" className="text-xs text-slate-500 mb-4" data-testid="breadcrumbs">
        <Link to="/" className="hover:text-ccn-tealdark">Naslovna</Link>
        {a.category && <> / <Link to={`/kategorija/${a.category.slug}`} className="hover:text-ccn-tealdark">{a.category.name}</Link></>}
      </nav>
      <div className="flex flex-wrap gap-2 mb-3">
        {a.category && <Link to={`/kategorija/${a.category.slug}`} className="bg-ccn-teal text-ccn-navy text-xs font-bold uppercase px-2 py-1 rounded-sm">{a.category.name}</Link>}
        {a.is_exclusive && <span className="bg-ccn-gold text-ccn-navy text-xs font-bold uppercase px-2 py-1 rounded-sm">Ekskluzivno</span>}
        {a.is_sponsored && <span className="bg-slate-200 text-slate-700 text-xs font-bold uppercase px-2 py-1 rounded-sm" data-testid="sponsored-label">Sponzorisani sadržaj</span>}
      </div>
      <h1 className="font-serif-news text-3xl sm:text-4xl lg:text-5xl font-black leading-[1.15]" data-testid="article-title">{a.title}</h1>
      {a.subtitle && <p className="mt-4 text-lg md:text-xl text-slate-600 leading-relaxed" data-testid="article-subtitle">{a.subtitle}</p>}
      <div className="mt-5 flex flex-wrap items-center justify-between gap-4 py-4 border-y border-ccn-mist">
        <div className="text-sm">
          <p className="font-semibold" data-testid="article-authors">
            {(a.authors || []).map((u, i) => <span key={u.id}>{i > 0 && ", "}<Link to={`/autor/${u.slug}`} className="hover:text-ccn-tealdark">{u.name}</Link></span>)}
            {!a.authors?.length && "Redakcija"}
          </p>
          <p className="text-slate-500 text-xs flex flex-wrap gap-3 mt-1">
            <span className="flex items-center gap-1"><Clock className="w-3 h-3" />{fmtDate(a.published_at || a.updated_at)}</span>
            {a.published_at && a.updated_at && a.updated_at.slice(0, 16) > a.published_at.slice(0, 16) && <span className="flex items-center gap-1" data-testid="article-updated"><RefreshCw className="w-3 h-3" />Ažurirano {fmtDate(a.updated_at)}</span>}
            {a.views !== undefined && <span className="flex items-center gap-1" data-testid="article-views"><Eye className="w-3 h-3" />{a.views} pregleda</span>}
          </p>
        </div>
        {!preview && <Share a={a} />}
      </div>
      {img && (
        <figure className="mt-6">
          <img src={mediaUrl(img.large)} alt={img.alt || a.title} className="w-full rounded-sm" data-testid="article-featured-image" />
          {(img.caption || img.credit) && <figcaption className="text-xs text-slate-500 mt-2">{img.caption} {img.credit && <span>Foto: {img.credit}</span>}</figcaption>}
        </figure>
      )}
      {a.summary && <p className="mt-6 font-semibold text-lg leading-relaxed border-l-4 border-ccn-teal pl-4">{a.summary}</p>}
      <div className="article-body mt-6" dangerouslySetInnerHTML={{ __html: b1 }} data-testid="article-body" />
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
      {!preview && <AdSlot position="below_article" className="mt-8" />}
      {!preview && a.comments_open && <Comments a={a} />}
      {!preview && a.related?.length > 0 && (
        <section className="mt-12" data-testid="related-articles">
          <h2 className="font-serif-news font-black text-xl mb-5">Povezane vijesti</h2>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-5">{a.related.slice(0, 6).map((r) => <ArticleCard key={r.id} a={r} />)}</div>
        </section>
      )}
    </article>
  );
}
