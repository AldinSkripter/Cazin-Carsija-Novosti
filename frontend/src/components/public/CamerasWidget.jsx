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
  useEffect(() => {
    api.get("/public/cameras").then((r) => setCams(r.data)).catch(() => {});
    const t = setInterval(() => setTick(Math.floor(Date.now() / 30000)), 30000);
    return () => clearInterval(t);
  }, []);
  if (!cams.length) return null;
  const shown = compact ? cams.slice(0, 4) : cams;
  return (
    <section className="relative bg-ccn-navy rounded-xl p-6 md:p-8 text-white overflow-hidden grain" data-testid="cameras-widget">
      <div className="flex items-center justify-between mb-5">
        <h2 className="flex items-center gap-2 font-bold text-base md:text-lg">
          <span className="relative flex h-2.5 w-2.5"><span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-ccn-red opacity-75" /><span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-ccn-red" /></span>
          <Video className="w-5 h-5 text-ccn-teal" /> {title}
        </h2>
        {compact && <Link to="/kamere" className="text-sm text-ccn-teal hover:underline" data-testid="cameras-all-link">Sve kamere →</Link>}
      </div>
      <div className={`grid gap-4 ${compact ? "grid-cols-2 lg:grid-cols-4" : "sm:grid-cols-2 lg:grid-cols-3"}`}>
        {shown.map((c) => (
          <button key={c.id} onClick={() => setOpen(c)} className="text-left group" data-testid={`camera-${c.id}`}>
            <div className="relative aspect-video overflow-hidden rounded-md bg-ccn-navy2 ring-1 ring-white/10 group-hover:ring-ccn-teal transition-all">
              <CamImage cam={c} tick={tick} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" />
              <span className="absolute top-2 left-2 bg-ccn-red text-[10px] font-bold px-1.5 py-0.5 rounded-sm uppercase">Uživo</span>
            </div>
            <p className="mt-2 text-sm font-semibold group-hover:text-ccn-teal transition-colors">{c.name}</p>
            <p className="text-xs text-white/50">{c.location}</p>
          </button>
        ))}
      </div>
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
