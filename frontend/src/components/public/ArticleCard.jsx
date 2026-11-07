import { Link } from "react-router-dom";
import { Clock, Eye, PlayCircle, Images, Star } from "lucide-react";
import { articleUrl, mediaUrl, timeAgo } from "../../lib/api";

const CAT_COLORS = {
  cazin: "#00C2B8", "unsko-sanski-kanton": "#0E7490", bihac: "#0E7490", "velika-kladusa": "#0E7490", "bosanska-krupa": "#0E7490", buzim: "#0E7490",
  "bosanski-petrovac": "#0E7490", "sanski-most": "#0E7490", kljuc: "#0E7490", "bosna-i-hercegovina": "#1D4ED8", region: "#0369A1", svijet: "#334155",
  politika: "#B45309", hronika: "#E1142B", drustvo: "#0F766E", ekonomija: "#047857", sport: "#16A34A", kultura: "#D4A52C", zdravlje: "#DB2777",
  obrazovanje: "#2563EB", zanimljivosti: "#EA580C", tehnologija: "#0891B2", video: "#E1142B", "foto-vijesti": "#D4A52C",
};
export const catColor = (c) => c?.color || CAT_COLORS[c?.slug] || "#00C2B8";

export function CatPill({ c, solid = true, className = "" }) {
  if (!c) return null;
  const col = catColor(c);
  return (
    <span className={`inline-block text-[10.5px] font-bold uppercase tracking-[0.12em] px-2 py-[3px] rounded-[3px] ${className}`}
      style={solid ? { background: col, color: col === "#D4A52C" || col === "#00C2B8" ? "#0B1F3B" : "#fff" } : { color: col }}>
      {c.name}
    </span>
  );
}

function Flags({ a }) {
  return (
    <>
      {a.is_exclusive && <span className="inline-flex items-center gap-1 text-[10px] font-extrabold uppercase bg-ccn-gold text-ccn-navy px-1.5 py-[3px] rounded-[3px]"><Star className="w-3 h-3" />Ekskluzivno</span>}
      {a.is_sponsored && <span className="text-[10px] font-bold uppercase bg-slate-200 text-slate-600 px-1.5 py-[3px] rounded-[3px]">Sponzorisano</span>}
    </>
  );
}

function Meta({ a, light }) {
  return (
    <p className={`text-[12px] mt-2 flex items-center gap-3 ${light ? "text-white/65" : "text-slate-500"}`}>
      <span className="flex items-center gap-1"><Clock className="w-3 h-3" />{timeAgo(a.published_at)}</span>
      {a.views > 0 && <span className="flex items-center gap-1"><Eye className="w-3 h-3" />{a.views}</span>}
    </p>
  );
}

function Thumb({ a, size = "medium", className = "" }) {
  const img = a.featured_image;
  return (
    <div className={`relative overflow-hidden bg-ccn-navy ${className}`}>
      {img ? (
        <img src={mediaUrl(img[size] || img.medium)} alt={img.alt || a.title} loading="lazy" className="card-img w-full h-full object-cover" />
      ) : (
        <div className="w-full h-full flex items-center justify-center"><img src="/icon-192.png" alt="" className="w-14 opacity-50" /></div>
      )}
      {a.has_video && <span className="absolute inset-0 flex items-center justify-center"><PlayCircle className="w-12 h-12 text-white drop-shadow-lg" strokeWidth={1.5} /></span>}
      {a.gallery?.length > 0 && <span className="absolute top-2 right-2 bg-black/60 text-white text-[11px] font-semibold px-1.5 py-0.5 rounded flex items-center gap-1"><Images className="w-3 h-3" />{a.gallery.length}</span>}
    </div>
  );
}

export function ArticleCard({ a, variant = "default", idx }) {
  const tid = `article-card-${a.slug}`;
  if (variant === "hero" || variant === "overlay") {
    const hero = variant === "hero";
    return (
      <Link to={articleUrl(a)} className={`news-card group block relative overflow-hidden rounded-lg ${hero ? "h-[380px] md:h-[520px]" : "h-[240px] md:h-[250px]"}`} data-testid={hero ? "hero-article" : tid}>
        <Thumb a={a} size={hero ? "large" : "medium"} className="absolute inset-0" />
        <div className="absolute inset-0 bg-gradient-to-t from-[#06111f] via-[#06111f]/55 to-transparent" />
        <div className={`absolute bottom-0 inset-x-0 ${hero ? "p-6 md:p-10" : "p-4 md:p-5"} text-white`}>
          <div className="flex flex-wrap gap-2 mb-3"><CatPill c={a.category} /><Flags a={a} /></div>
          <h2 className={`font-serif-news font-black leading-[1.15] group-hover:text-ccn-teal transition-colors ${hero ? "text-[26px] md:text-[44px] max-w-3xl" : "text-lg md:text-xl line-clamp-3"}`}>{a.title}</h2>
          {hero && a.subtitle && <p className="mt-4 text-white/80 text-[15px] md:text-lg max-w-2xl line-clamp-2 leading-relaxed">{a.subtitle}</p>}
          <Meta a={a} light />
        </div>
      </Link>
    );
  }
  if (variant === "list") {
    return (
      <Link to={articleUrl(a)} className="news-card group flex gap-4 py-3.5 border-b border-ccn-mist last:border-0" data-testid={tid}>
        {idx !== undefined ? (
          <span className="font-serif-news text-[34px] font-black text-ccn-gold/90 w-9 shrink-0 leading-none tabular-nums">{idx + 1}</span>
        ) : (
          <Thumb a={a} size="thumb" className="w-[104px] h-[70px] shrink-0 rounded-md" />
        )}
        <div className="min-w-0">
          {idx === undefined && <CatPill c={a.category} solid={false} className="!px-0 !py-0 mb-1" />}
          <h3 className="news-title font-semibold text-[15px] leading-snug line-clamp-3 transition-colors">{a.title}</h3>
          <Meta a={a} />
        </div>
      </Link>
    );
  }
  if (variant === "dark") {
    return (
      <Link to={articleUrl(a)} className="news-card block group" data-testid={tid}>
        <Thumb a={a} className="aspect-video rounded-md" />
        <h3 className="mt-3 font-semibold text-white leading-snug line-clamp-3 group-hover:text-ccn-teal transition-colors">{a.title}</h3>
        <Meta a={a} light />
      </Link>
    );
  }
  if (variant === "compact") {
    return (
      <Link to={articleUrl(a)} className="news-card group block py-3 border-b border-ccn-mist last:border-0" data-testid={tid}>
        <CatPill c={a.category} solid={false} className="!px-0 !py-0" />
        <h3 className="news-title font-serif-news font-bold text-[16px] leading-snug mt-1 transition-colors">{a.title}</h3>
        <Meta a={a} />
      </Link>
    );
  }
  const wide = variant === "wide";
  return (
    <Link to={articleUrl(a)} className="news-card block group h-full" data-testid={tid}>
      <div className="relative">
        <Thumb a={a} size={wide ? "large" : "medium"} className={`${wide ? "aspect-[16/9]" : "aspect-[3/2]"} rounded-md`} />
        {a.category && <CatPill c={a.category} className="absolute left-3 bottom-3 shadow" />}
      </div>
      <div className="pt-3.5">
        <div className="flex gap-1.5 mb-1.5 empty:hidden"><Flags a={a} /></div>
        <h3 className={`news-title font-serif-news font-bold leading-snug transition-colors ${wide ? "text-[22px] md:text-[26px]" : "text-[17px] line-clamp-3"}`}>{a.title}</h3>
        {wide && a.summary && <p className="text-[15px] text-slate-600 mt-2.5 line-clamp-3 leading-relaxed">{a.summary}</p>}
        <Meta a={a} />
      </div>
    </Link>
  );
}
