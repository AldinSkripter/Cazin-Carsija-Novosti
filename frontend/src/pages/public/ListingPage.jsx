import { useEffect, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import { api } from "../../lib/api";
import { useSeo } from "../../lib/seo";
import { useSite } from "../../lib/auth";
import { ArticleCard } from "../../components/public/ArticleCard";
import { AdSlot } from "../../components/public/AdSlot";
import { MostRead, SectionTitle } from "../../components/public/HomeBlocks";
import NotFound from "./NotFound";

function SearchForm({ params, setParams, cats }) {
  const [f, setF] = useState({ q: params.get("q") || "", category: params.get("category") || "", author: params.get("author") || "", date_from: params.get("date_from") || "", date_to: params.get("date_to") || "" });
  const [authors, setAuthors] = useState([]);
  useEffect(() => { api.get("/public/authors").then((r) => setAuthors(r.data)).catch(() => {}); }, []);
  const submit = (e) => { e.preventDefault(); setParams(Object.fromEntries(Object.entries(f).filter(([, v]) => v))); };
  const cls = "border border-slate-300 rounded-sm px-3 py-2 text-sm bg-white";
  return (
    <form onSubmit={submit} className="grid sm:grid-cols-2 lg:grid-cols-3 gap-2 mb-8" data-testid="search-form">
      <input value={f.q} onChange={(e) => setF({ ...f, q: e.target.value })} placeholder="Pojam (npr. čaršija, Bužim…)" className={`${cls} sm:col-span-2 lg:col-span-3`} data-testid="search-query" />
      <select value={f.category} onChange={(e) => setF({ ...f, category: e.target.value })} className={cls} data-testid="search-category">
        <option value="">Sve kategorije</option>{cats.map((c) => <option key={c.id} value={c.slug}>{c.name}</option>)}
      </select>
      <select value={f.author} onChange={(e) => setF({ ...f, author: e.target.value })} className={cls} data-testid="search-author">
        <option value="">Svi autori</option>{authors.map((u) => <option key={u.id} value={u.slug}>{u.name}</option>)}
      </select>
      <input type="date" value={f.date_from} onChange={(e) => setF({ ...f, date_from: e.target.value })} className={cls} aria-label="Od datuma" data-testid="search-from" />
      <div className="flex gap-2 min-w-0">
        <input type="date" value={f.date_to} onChange={(e) => setF({ ...f, date_to: e.target.value })} className={`${cls} flex-1 min-w-0`} aria-label="Do datuma" data-testid="search-to" />
        <button className="bg-ccn-teal text-ccn-navy font-bold px-5 rounded-sm text-sm hover:bg-ccn-gold transition-colors" data-testid="search-submit">Traži</button>
      </div>
    </form>
  );
}

export default function ListingPage({ mode }) {
  const { slug, tag } = useParams();
  const [params, setParams] = useSearchParams();
  const { site, cats } = useSite();
  const [data, setData] = useState(null);
  const [meta, setMeta] = useState(null);
  const [err, setErr] = useState(false);
  const page = Number(params.get("page") || 1);
  const qs = params.toString();
  useEffect(() => {
    const p = { page, limit: 18 };
    if (mode === "category") p.category = slug;
    if (mode === "tag") p.tag = tag;
    if (mode === "author") p.author = slug;
    if (mode === "search") Object.assign(p, Object.fromEntries(new URLSearchParams(qs)));
    if (mode === "search" && !p.q && !p.category && !p.author && !p.date_from) { setData({ items: [], total: 0 }); return; }
    setErr(false);
    api.get("/public/articles", { params: p }).then((r) => setData(r.data)).catch(() => setErr(true));
    if (mode === "author") api.get(`/public/authors/${slug}`).then((r) => setMeta(r.data)).catch(() => setErr(true));
  }, [mode, slug, tag, page, qs]);
  const cat = mode === "category" ? cats.find((c) => c.slug === slug) : null;
  const title = { category: cat?.name, tag: `#${tag}`, author: meta?.name, search: "Pretraga", archive: "Arhiva vijesti" }[mode];
  useSeo({ siteName: site.site_name, title: cat?.seo_title?.split(" – ")[0] || title, description: cat?.seo_description || cat?.description, noindex: mode === "search" });
  if (err) return <NotFound />;
  const subs = cat ? cats.filter((c) => c.parent_id === cat.id) : [];
  const pages = data ? Math.ceil(data.total / 18) : 0;
  return (
    <div className="max-w-7xl mx-auto px-4 py-8 grid lg:grid-cols-12 gap-10" data-testid={`listing-${mode}`}>
      <div className="lg:col-span-8">
        <SectionTitle title={title || ""} />
        {cat?.description && <p className="text-slate-600 -mt-2 mb-6">{cat.description}</p>}
        {meta?.bio && <p className="text-slate-600 -mt-2 mb-6">{meta.bio}</p>}
        {subs.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-6" data-testid="subcategories">
            {subs.map((s) => <a key={s.id} href={`/kategorija/${s.slug}`} className="text-sm px-3 py-1 border rounded-full hover:bg-ccn-teal">{s.name}</a>)}
          </div>
        )}
        {mode === "search" && <SearchForm params={params} setParams={setParams} cats={cats} />}
        {data && <p className="text-sm text-slate-500 mb-4" data-testid="listing-total">{data.total} {data.total % 10 === 1 && data.total % 100 !== 11 ? "rezultat" : "rezultata"}</p>}
        <div className="grid grid-cols-2 md:grid-cols-3 gap-x-5 gap-y-8">
          {data?.items.map((a, i) => (
            <div key={a.id} className="contents">
              <ArticleCard a={a} />
              {i === 5 && <div className="col-span-2 md:col-span-3"><AdSlot position="between_cards" /></div>}
            </div>
          ))}
        </div>
        {pages > 1 && (
          <div className="flex gap-2 mt-10" data-testid="pagination">
            {Array.from({ length: Math.min(pages, 10) }, (_, i) => i + 1).map((n) => (
              <button key={n} onClick={() => { params.set("page", n); setParams(params); }} data-testid={`page-${n}`}
                className={`w-9 h-9 rounded-sm text-sm font-semibold ${n === page ? "bg-ccn-navy text-white" : "bg-white border"}`}>{n}</button>
            ))}
          </div>
        )}
      </div>
      <aside className="lg:col-span-4 space-y-6"><AdSlot position="sidebar" /><MostRead /></aside>
    </div>
  );
}
