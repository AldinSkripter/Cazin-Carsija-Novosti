import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Flame, ArrowRight, Hash } from "lucide-react";
import { api } from "../../lib/api";
import { ArticleCard, catColor } from "./ArticleCard";
import { AdSlot } from "./AdSlot";
import { CamerasWidget } from "./CamerasWidget";
import { WeatherWidget } from "./WeatherWidget";

export function SectionTitle({ title, to, dark, color = "#D4A52C" }) {
  return (
    <div className="flex items-center gap-4 mb-6">
      <h2 className={`font-serif-news text-[22px] md:text-[26px] font-black whitespace-nowrap flex items-center gap-3 ${dark ? "text-white" : "text-ccn-navy"}`}>
        <span className="w-1.5 h-7 rounded-full" style={{ background: color }} />{title}
      </h2>
      <span className={`flex-1 h-px ${dark ? "bg-white/15" : "bg-ccn-navy/15"}`} />
      {to && (
        <Link to={to} className={`group text-[13px] font-bold uppercase tracking-wider flex items-center gap-1 whitespace-nowrap ${dark ? "text-ccn-teal" : "text-ccn-tealdark"}`}>
          Sve <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
        </Link>
      )}
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
    <section className="bg-white rounded-lg border border-ccn-mist shadow-sm overflow-hidden" data-testid="most-read">
      <h2 className="flex items-center gap-2 px-5 py-3.5 bg-ccn-navy text-white font-bold text-sm uppercase tracking-[0.15em]">
        <Flame className="w-4 h-4 text-ccn-red" /> Najčitanije
      </h2>
      <div className="px-5 py-1">{items.map((a, i) => <ArticleCard key={a.id} a={a} variant="list" idx={i} />)}</div>
    </section>
  );
}

function PopularTags() {
  const [tags, setTags] = useState([]);
  useEffect(() => { api.get("/public/tags/popular").then((r) => setTags(r.data)).catch(() => {}); }, []);
  if (!tags.length) return null;
  return (
    <div className="flex flex-wrap gap-2.5" data-testid="popular-tags">
      {tags.map((t, i) => (
        <Link key={t.name} to={`/tema/${encodeURIComponent(t.name)}`}
          className={`flex items-center gap-1 px-4 py-2 rounded-full text-sm font-semibold border transition-all hover:-translate-y-0.5 ${i < 3 ? "bg-ccn-navy text-white border-ccn-navy hover:bg-ccn-teal hover:text-ccn-navy hover:border-ccn-teal" : "bg-white border-ccn-mist hover:border-ccn-teal hover:text-ccn-tealdark"}`}>
          <Hash className="w-3.5 h-3.5 opacity-60" />{t.name}
        </Link>
      ))}
    </div>
  );
}

function Hero({ items }) {
  if (!items?.length) return null;
  const [main, second, third, ...rest] = items;
  return (
    <div className="grid lg:grid-cols-12 gap-5 fade-up" data-testid="home-hero">
      <div className="lg:col-span-7 xl:col-span-8"><ArticleCard a={main} variant="hero" /></div>
      <div className="lg:col-span-5 xl:col-span-4 grid sm:grid-cols-2 lg:grid-cols-1 gap-5">
        {[second, third].filter(Boolean).map((a) => <ArticleCard key={a.id} a={a} variant="overlay" />)}
      </div>
      {rest.length > 0 && (
        <div className="lg:col-span-12 grid sm:grid-cols-2 lg:grid-cols-4 gap-x-6 bg-white rounded-lg border border-ccn-mist px-5">
          {rest.map((a) => <ArticleCard key={a.id} a={a} variant="compact" />)}
        </div>
      )}
    </div>
  );
}

function Grid({ b }) {
  if (!b.articles?.length) return null;
  const isCat = b.type === "category";
  const [first, ...rest] = b.articles;
  const color = isCat ? catColor(first.category) : undefined;
  return (
    <section data-testid={`home-block-${b.type}`} className="fade-up">
      <SectionTitle title={b.title} color={color} to={b.category_slug ? `/kategorija/${b.category_slug}` : b.type === "latest" ? "/arhiva" : null} />
      {isCat ? (
        <div className="grid md:grid-cols-2 gap-6">
          <ArticleCard a={first} variant="wide" />
          <div className="flex flex-col">{rest.map((a) => <ArticleCard key={a.id} a={a} variant="list" />)}</div>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-x-6 gap-y-9">
          {b.articles.map((a) => <ArticleCard key={a.id} a={a} />)}
        </div>
      )}
    </section>
  );
}

function DarkGrid({ b, to }) {
  if (!b.articles?.length) return null;
  return (
    <section className="relative bg-ccn-navy rounded-xl p-6 md:p-9 overflow-hidden grain" data-testid={`home-block-${b.type}`}>
      <SectionTitle title={b.title} dark to={to} color={b.type === "video" ? "#E1142B" : "#D4A52C"} />
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-6 relative">
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
    case "popular_tags": return <section><SectionTitle title={b.title || "Popularne teme"} color="#00C2B8" /><PopularTags /></section>;
    default: return null;
  }
}
