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
    <div className="bg-ccn-red text-white border-t border-black/10" data-testid="breaking-ticker" role="region" aria-label="Hitne vijesti">
      <div className="max-w-7xl mx-auto px-4 flex items-stretch h-10">
        <span className="relative z-10 shrink-0 flex items-center gap-1.5 bg-[#A50D1F] pl-3 pr-4 text-[11px] font-extrabold uppercase tracking-[0.2em] -ml-4 sm:ml-0"
          style={{ clipPath: "polygon(0 0, 100% 0, calc(100% - 10px) 100%, 0 100%)", paddingRight: "1.4rem" }}>
          <Zap className="w-4 h-4 text-ccn-gold" /> Hitno
        </span>
        <div className="ticker-wrap relative overflow-hidden flex-1 flex items-center">
          <div className="ticker-track pl-5">
            {list.map((b, i) => {
              const to = b.article_slug ? `/vijesti/${b.article_slug}` : b.url;
              const text = <span className="font-semibold text-sm flex items-center gap-3"><span className="w-1.5 h-1.5 rounded-full bg-white/70" />{b.title}</span>;
              return to ? (
                <Link key={i} to={to} className="hover:underline" data-testid={`breaking-item-${i}`}>{text}</Link>
              ) : <span key={i}>{text}</span>;
            })}
          </div>
          <span className="pointer-events-none absolute right-0 inset-y-0 w-10 bg-gradient-to-l from-ccn-red to-transparent" />
        </div>
      </div>
    </div>
  );
}
