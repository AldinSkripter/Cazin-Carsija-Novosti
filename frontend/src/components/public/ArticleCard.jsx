import { Link } from "react-router-dom";
import { Clock, Eye, PlayCircle, Images } from "lucide-react";
import { articleUrl, mediaUrl, timeAgo } from "../../lib/api";

function Badges({ a }) {
  return (
    <div className="flex flex-wrap gap-1.5 mb-2">
      {a.category && <span className="text-[11px] font-semibold uppercase tracking-wider text-ccn-tealdark">{a.category.name}</span>}
      {a.is_exclusive && <span className="text-[10px] font-bold uppercase bg-ccn-gold text-ccn-navy px-1.5 py-0.5 rounded-sm">Ekskluzivno</span>}
      {a.is_sponsored && <span className="text-[10px] font-bold uppercase bg-slate-200 text-slate-600 px-1.5 py-0.5 rounded-sm">Sponzorisano</span>}
    </div>
  );
}

function Thumb({ a, size = "medium", className = "" }) {
  const img = a.featured_image;
  return (
    <div className={`relative overflow-hidden bg-ccn-mist ${className}`}>
      {img ? (
        <img src={mediaUrl(img[size] || img.medium)} alt={img.alt || a.title} loading="lazy" className="w-full h-full object-cover" />
      ) : (
        <div className="w-full h-full flex items-center justify-center bg-ccn-navy"><img src="/icon-192.png" alt="" className="w-14 opacity-60" /></div>
      )}
      {a.has_video && <PlayCircle className="absolute bottom-2 left-2 w-8 h-8 text-white drop-shadow" />}
      {a.gallery?.length > 0 && <Images className="absolute bottom-2 right-2 w-6 h-6 text-white drop-shadow" />}
    </div>
  );
}

export function ArticleCard({ a, variant = "default", idx }) {
  const tid = `article-card-${a.slug}`;
  if (variant === "hero") {
    return (
      <Link to={articleUrl(a)} className="news-card group block relative h-[360px] md:h-[480px] overflow-hidden rounded-md" data-testid="hero-article">
        <Thumb a={a} size="large" className="absolute inset-0" />
        <div className="absolute inset-0 bg-gradient-to-t from-ccn-navy via-ccn-navy/60 to-transparent" />
        <div className="absolute bottom-0 p-5 md:p-8 text-white">
          <div className="flex gap-2 mb-3">
            {a.category && <span className="bg-ccn-teal text-ccn-navy text-xs font-bold uppercase px-2 py-1 rounded-sm">{a.category.name}</span>}
            {a.is_exclusive && <span className="bg-ccn-gold text-ccn-navy text-xs font-bold uppercase px-2 py-1 rounded-sm">Ekskluzivno</span>}
          </div>
          <h2 className="font-serif-news text-2xl md:text-4xl font-black leading-tight">{a.title}</h2>
          {a.subtitle && <p className="mt-3 text-white/80 text-sm md:text-base max-w-2xl line-clamp-2">{a.subtitle}</p>}
          <p className="mt-3 text-xs text-white/60 flex items-center gap-1"><Clock className="w-3 h-3" /> {timeAgo(a.published_at)}</p>
        </div>
      </Link>
    );
  }
  if (variant === "list") {
    return (
      <Link to={articleUrl(a)} className="news-card flex gap-3 py-3 border-b border-ccn-mist last:border-0" data-testid={tid}>
        {idx !== undefined ? (
          <span className="font-serif-news text-3xl font-black text-ccn-gold w-8 shrink-0 leading-none">{idx + 1}</span>
        ) : (
          <Thumb a={a} size="thumb" className="w-24 h-16 shrink-0 rounded-sm" />
        )}
        <div className="min-w-0">
          <h3 className="news-title font-semibold text-[15px] leading-snug line-clamp-3 transition-colors">{a.title}</h3>
          <p className="text-xs text-slate-500 mt-1 flex items-center gap-2">
            {timeAgo(a.published_at)}{a.views !== undefined && <span className="flex items-center gap-0.5"><Eye className="w-3 h-3" />{a.views}</span>}
          </p>
        </div>
      </Link>
    );
  }
  if (variant === "dark") {
    return (
      <Link to={articleUrl(a)} className="news-card block group" data-testid={tid}>
        <Thumb a={a} className="aspect-video rounded-sm" />
        <h3 className="mt-3 font-semibold text-white leading-snug line-clamp-3 group-hover:text-ccn-teal transition-colors">{a.title}</h3>
        <p className="text-xs text-white/50 mt-1">{timeAgo(a.published_at)}</p>
      </Link>
    );
  }
  return (
    <Link to={articleUrl(a)} className="news-card block group" data-testid={tid}>
      <Thumb a={a} className="aspect-[16/10] rounded-sm" />
      <div className="pt-3">
        <Badges a={a} />
        <h3 className="news-title font-serif-news font-bold text-[17px] leading-snug line-clamp-3 transition-colors">{a.title}</h3>
        {variant === "wide" && a.summary && <p className="text-sm text-slate-600 mt-2 line-clamp-2">{a.summary}</p>}
        <p className="text-xs text-slate-500 mt-2">{timeAgo(a.published_at)}</p>
      </div>
    </Link>
  );
}
