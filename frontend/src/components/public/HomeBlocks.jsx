import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../lib/api";
import { ArticleCard } from "./ArticleCard";
import { AdSlot } from "./AdSlot";
import { CamerasWidget } from "./CamerasWidget";
import { WeatherWidget } from "./WeatherWidget";

export function SectionTitle({ title, to, dark }) {
  return (
    <div className={`flex items-end justify-between mb-5 pb-2 border-b-2 ${dark ? "border-white/15" : "border-ccn-navy"}`}>
      <h2 className={`font-serif-news text-xl md:text-2xl font-black relative ${dark ? "text-white" : "text-ccn-navy"}`}>
        <span className="absolute -bottom-[10px] left-0 w-12 h-[3px] bg-ccn-gold" />{title}
      </h2>
      {to && <Link to={to} className="text-sm font-semibold text-ccn-tealdark hover:underline">Više →</Link>}
    </div>
  );
}

export function MostRead({ limit = 5 }) {
  const [items, setItems] = useState([]);
  useEffect(() => {
    api.get("/public/articles", { params: { sort: "popular", limit } }).then((r) => setItems(r.data.items)).catch(() => {});
  }, [limit]);
  if (!items.length) return null;
  return (
    <section className="bg-white rounded-md border border-ccn-mist p-5" data-testid="most-read">
      <h2 className="text-xs font-bold uppercase tracking-widest text-ccn-red mb-2">Najčitanije</h2>
      {items.map((a, i) => <ArticleCard key={a.id} a={a} variant="list" idx={i} />)}
    </section>
  );
}

function PopularTags() {
  const [tags, setTags] = useState([]);
  useEffect(() => { api.get("/public/tags/popular").then((r) => setTags(r.data)).catch(() => {}); }, []);
  if (!tags.length) return null;
  return (
    <div className="flex flex-wrap gap-2" data-testid="popular-tags">
      {tags.map((t) => (
        <Link key={t.name} to={`/tema/${encodeURIComponent(t.name)}`} className="px-3 py-1.5 bg-white border border-ccn-mist rounded-full text-sm font-medium hover:bg-ccn-teal hover:border-ccn-teal transition-colors">#{t.name}</Link>
      ))}
    </div>
  );
}

function Hero({ items }) {
  if (!items?.length) return null;
  const [main, ...rest] = items;
  return (
    <div className="grid lg:grid-cols-12 gap-5 fade-up">
      <div className="lg:col-span-8"><ArticleCard a={main} variant="hero" /></div>
      <div className="lg:col-span-4 bg-white rounded-md border border-ccn-mist px-4 py-1">
        {rest.slice(0, 4).map((a) => <ArticleCard key={a.id} a={a} variant="list" />)}
      </div>
    </div>
  );
}

function Grid({ b, cols = 4 }) {
  if (!b.articles?.length) return null;
  return (
    <section data-testid={`home-block-${b.type}`}>
      <SectionTitle title={b.title} to={b.category_slug ? `/kategorija/${b.category_slug}` : b.type === "latest" ? "/arhiva" : null} />
      <div className={`grid grid-cols-2 gap-x-5 gap-y-8 ${cols === 4 ? "lg:grid-cols-4" : "lg:grid-cols-3"}`}>
        {b.articles.map((a, i) => (
          <div key={a.id} className={i === 0 && b.type === "category" ? "col-span-2 lg:col-span-2 lg:row-span-2" : ""}>
            <ArticleCard a={a} variant={i === 0 && b.type === "category" ? "wide" : "default"} />
          </div>
        ))}
      </div>
    </section>
  );
}

function DarkGrid({ b, to }) {
  if (!b.articles?.length) return null;
  return (
    <section className="bg-ccn-navy rounded-md p-5 md:p-7" data-testid={`home-block-${b.type}`}>
      <SectionTitle title={b.title} dark to={to} />
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-5">
        {b.articles.map((a) => <ArticleCard key={a.id} a={a} variant="dark" />)}
      </div>
    </section>
  );
}

export function HomeBlock({ b }) {
  switch (b.type) {
    case "hero": return <Hero items={b.articles} />;
    case "latest":
    case "category":
    case "manual": return <Grid b={b} />;
    case "most_read": return <MostRead limit={b.limit || 5} />;
    case "video": return <DarkGrid b={b} to="/kategorija/video" />;
    case "gallery": return <DarkGrid b={b} to="/kategorija/foto-vijesti" />;
    case "ad": return <AdSlot position={b.ad_position || "home_top"} />;
    case "cameras": return <CamerasWidget title={b.title} compact />;
    case "weather": return <WeatherWidget />;
    case "popular_tags": return <section><SectionTitle title={b.title || "Popularne teme"} /><PopularTags /></section>;
    default: return null;
  }
}
