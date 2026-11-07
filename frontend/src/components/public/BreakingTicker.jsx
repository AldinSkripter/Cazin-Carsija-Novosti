import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Zap } from "lucide-react";
import { api } from "../../lib/api";

export function BreakingTicker() {
  const [items, setItems] = useState([]);
  useEffect(() => {
    const load = () => api.get("/public/breaking").then((r) => setItems(r.data)).catch(() => {});
    load();
    const t = setInterval(load, 60000);
    return () => clearInterval(t);
  }, []);
  if (!items.length) return null;
  const list = [...items, ...items];
  return (
    <div className="bg-ccn-red text-white" data-testid="breaking-ticker" role="region" aria-label="Hitne vijesti">
      <div className="max-w-7xl mx-auto flex items-center">
        <span className="shrink-0 flex items-center gap-1.5 bg-[#B30E21] px-3 md:px-5 py-2.5 text-xs font-extrabold uppercase tracking-[0.2em]">
          <Zap className="w-4 h-4 text-ccn-gold animate-pulse" /> Hitno
        </span>
        <div className="ticker-wrap overflow-hidden flex-1 py-2.5" style={{ maskImage: "linear-gradient(90deg, transparent, #000 4%, #000 96%, transparent)" }}>
          <div className="ticker-track pl-6">
            {list.map((b, i) => {
              const to = b.article_slug ? `/vijesti/${b.article_slug}` : b.url;
              const text = <span className="font-semibold text-sm flex items-center gap-3"><span className="w-1.5 h-1.5 rounded-full bg-white/70" />{b.title}</span>;
              return to ? (
                <Link key={i} to={to} className="hover:underline" data-testid={`breaking-item-${i}`}>{text}</Link>
              ) : <span key={i}>{text}</span>;
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
