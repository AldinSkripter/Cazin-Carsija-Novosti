import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Video, X, RefreshCw, ExternalLink } from "lucide-react";
import { api, BACKEND } from "../../lib/api";
import { Dialog, DialogContent, DialogTitle } from "../ui/dialog";

function CamImage({ cam, tick, className }) {
  return (
    <img src={`${BACKEND}/api/public/cameras/${cam.id}/image?t=${tick}`} alt={`Kamera uživo: ${cam.name}`}
      className={className} loading="lazy" onError={(e) => { e.currentTarget.style.opacity = 0.2; }} />
  );
}

export function CamerasWidget({ title = "Kamere uživo sa granica", compact = false }) {
  const [cams, setCams] = useState([]);
  const [tick, setTick] = useState(Math.floor(Date.now() / 60000));
  const [open, setOpen] = useState(null);
  const [group, setGroup] = useState("");
  const [q, setQ] = useState("");
  useEffect(() => {
    api.get("/public/cameras").then((r) => setCams(r.data)).catch(() => {});
    const t = setInterval(() => setTick(Math.floor(Date.now() / 30000)), 30000);
    return () => clearInterval(t);
  }, []);
  if (!cams.length) return null;
  const groups = [...new Set(cams.map((c) => c.group || "Ostalo"))];
  const ql = q.toLowerCase();
  const shown = compact ? cams.slice(0, 4) : cams.filter((c) => (!group || (c.group || "Ostalo") === group) && (!ql || `${c.name} ${c.location}`.toLowerCase().includes(ql)));
  return (
    <section className="relative bg-ccn-navy rounded-xl p-6 md:p-8 text-white overflow-hidden grain" data-testid="cameras-widget">
      <div className="flex items-center justify-between mb-5">
        <h2 className="flex items-center gap-2 font-bold text-base md:text-lg">
          <span className="relative flex h-2.5 w-2.5"><span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-ccn-red opacity-75" /><span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-ccn-red" /></span>
          <Video className="w-5 h-5 text-ccn-teal" /> {title}
        </h2>
        {compact && <Link to="/kamere" className="text-sm text-ccn-teal hover:underline" data-testid="cameras-all-link">Sve kamere →</Link>}
      </div>
      {!compact && (
        <div className="flex flex-wrap gap-2 mb-6" data-testid="cameras-filters">
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Traži prijelaz (npr. Maljevac)…" aria-label="Traži kameru" data-testid="cameras-search"
            className="rounded-full px-4 py-2 text-sm bg-white/10 border border-white/20 text-white placeholder-white/50 w-full sm:w-64" />
          {["", ...groups].map((g) => (
            <button key={g || "all"} onClick={() => setGroup(g)} data-testid={`cameras-group-${g || "all"}`}
              className={`px-3 py-1.5 rounded-full text-sm font-semibold transition-colors ${group === g ? "bg-ccn-teal text-ccn-navy" : "bg-white/10 hover:bg-white/20"}`}>
              {g || `Sve (${cams.length})`}
            </button>
          ))}
        </div>
      )}
      <div className={`grid gap-4 ${compact ? "grid-cols-2 lg:grid-cols-4" : "sm:grid-cols-2 lg:grid-cols-4"}`}>
        {shown.map((c) => (
          <button key={c.id} onClick={() => setOpen(c)} className="text-left group" data-testid={`camera-${c.id}`}>
            <div className="relative aspect-video overflow-hidden rounded-md bg-ccn-navy2 ring-1 ring-white/10 group-hover:ring-ccn-teal transition-all">
              <CamImage cam={c} tick={tick} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" />
              <span className="absolute top-2 left-2 bg-ccn-red text-[10px] font-bold px-1.5 py-0.5 rounded-sm uppercase">Uživo</span>
            </div>
            <p className="mt-2 text-sm font-semibold group-hover:text-ccn-teal transition-colors">{c.name}</p>
            <p className="text-xs text-white/50">{c.location}{!compact && c.group ? ` · ${c.group}` : ""}</p>
          </button>
        ))}
      </div>
      {!compact && !shown.length && <p className="text-white/60 text-sm py-6" data-testid="cameras-empty">Nema kamera za zadanu pretragu.</p>}
      <p className="mt-4 text-[11px] text-white/40 flex items-center gap-1"><RefreshCw className="w-3 h-3" /> Slike se automatski osvježavaju. Izvor: HAK.</p>
      <Dialog open={!!open} onOpenChange={() => setOpen(null)}>
        <DialogContent className="max-w-4xl bg-ccn-navy text-white border-ccn-navy2" data-testid="camera-modal">
          {open && (
            <>
              <DialogTitle className="text-white">{open.name}</DialogTitle>
              <CamImage cam={open} tick={tick} className="w-full rounded-sm" />
              <div className="flex justify-between text-sm text-white/60">
                <span>{open.location} · {open.description}</span>
                {open.page_url && <a href={open.page_url} target="_blank" rel="noopener noreferrer" className="text-ccn-teal flex items-center gap-1">Izvor <ExternalLink className="w-3 h-3" /></a>}
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </section>
  );
}
