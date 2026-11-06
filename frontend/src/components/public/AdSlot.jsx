import { useEffect, useState } from "react";
import { api, mediaUrl } from "../../lib/api";

const cache = {};
const pending = {};

function fetchAds(positions) {
  const key = positions.join(",");
  if (!pending[key]) pending[key] = api.get("/public/ads", { params: { positions: key } }).then((r) => r.data).catch(() => ({}));
  return pending[key];
}

export function AdSlot({ position, className = "", minH = 0 }) {
  const [ad, setAd] = useState(cache[position]);
  useEffect(() => {
    let live = true;
    fetchAds([position]).then((d) => {
      if (!live) return;
      cache[position] = d[position] || null;
      setAd(cache[position]);
      if (d[position]) api.post(`/public/ads/${d[position].id}/impression`).catch(() => {});
    });
    return () => { live = false; };
  }, [position]);
  if (!ad) return null;
  return (
    <aside className={`w-full ${className}`} data-testid={`ad-slot-${position}`} aria-label="Reklama">
      <div className="text-[10px] uppercase tracking-[0.2em] text-slate-400 mb-1">{ad.sponsored_label || "Oglas"}</div>
      {ad.type === "image" || !ad.type ? (
        <a href={`${process.env.REACT_APP_BACKEND_URL}/api/public/ads/${ad.id}/click`} target="_blank" rel="sponsored noopener noreferrer">
          <picture>
            {ad.mobile_image_url && <source media="(max-width: 640px)" srcSet={mediaUrl(ad.mobile_image_url)} />}
            <img src={mediaUrl(ad.image_url)} alt={ad.alt || ad.name} loading="lazy" className="w-full h-auto rounded-sm" />
          </picture>
        </a>
      ) : (
        <iframe title={ad.name} srcDoc={ad.html_code} sandbox="allow-scripts allow-popups allow-popups-to-escape-sandbox"
          className="w-full border-0" style={{ minHeight: minH || 250 }} loading="lazy" />
      )}
    </aside>
  );
}
