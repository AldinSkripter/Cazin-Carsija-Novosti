import { useEffect, useState } from "react";
import { Tv } from "lucide-react";
import { Dialog, DialogContent, DialogTitle } from "../ui/dialog";

const STREAM = "https://crt-stream.loopstudiobih.dev/embed/";
const EVT = "ccn-rtv-open";

export const RtvLive = ({ big = false, onOpen }) => {
  const show = () => { onOpen?.(); setTimeout(() => window.dispatchEvent(new Event(EVT)), 0); };
  return (
    <button onClick={show} data-testid={big ? "rtv-live-mobile" : "rtv-live-button"}
      className={big ? "mt-3 flex items-center justify-center gap-2 bg-ccn-red text-white font-bold py-3 rounded-full"
        : "shrink-0 flex items-center gap-2 text-sm font-bold bg-ccn-red text-white px-4 py-2.5 rounded-full hover:brightness-110 hover:-translate-y-0.5 transition-[filter,transform] whitespace-nowrap"}>
      <span className="w-2 h-2 rounded-full bg-white animate-pulse" /><Tv className="w-4 h-4" />{big ? "Gledaj RTV Cazin uživo" : <><span className="xl:hidden">RTV uživo</span><span className="hidden xl:inline">Gledaj RTV Cazin uživo</span></>}
    </button>
  );
};

export const RtvPlayer = () => {
  const [open, setOpen] = useState(false);
  useEffect(() => {
    const on = () => setOpen(true);
    window.addEventListener(EVT, on);
    return () => window.removeEventListener(EVT, on);
  }, []);
  if (!open) return null;
  return (
    <Dialog open onOpenChange={setOpen}>
      <DialogContent className="w-[calc(100vw-16px)] max-w-4xl p-3 bg-black border-0" data-testid="rtv-live-dialog">
        <DialogTitle className="text-white text-sm flex items-center gap-2 px-1"><span className="w-2 h-2 rounded-full bg-ccn-red animate-pulse" />RTV Cazin – uživo</DialogTitle>
        <div className="relative w-full aspect-video bg-black rounded overflow-hidden">
          <iframe src={STREAM} title="RTV Cazin uživo" className="absolute inset-0 w-full h-full" allow="autoplay; fullscreen; encrypted-media; picture-in-picture" allowFullScreen data-testid="rtv-live-iframe" />
        </div>
      </DialogContent>
    </Dialog>
  );
};
