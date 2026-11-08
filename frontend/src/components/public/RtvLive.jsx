import { useState } from "react";
import { Tv } from "lucide-react";
import { Dialog, DialogContent, DialogTitle } from "../ui/dialog";

const STREAM = "https://crt-stream.loopstudiobih.dev/embed/";

export const RtvLive = ({ big = false, onOpen }) => {
  const [open, setOpen] = useState(false);
  const show = () => { onOpen?.(); setOpen(true); };
  return (
    <>
      <button onClick={show} data-testid={big ? "rtv-live-mobile" : "rtv-live-button"}
        className={big ? "mt-3 flex items-center justify-center gap-2 bg-ccn-red text-white font-bold py-3 rounded-full"
          : "ml-2 shrink-0 flex items-center gap-1.5 text-[12px] font-bold uppercase tracking-wider bg-ccn-red text-white px-3 py-1.5 rounded-full hover:brightness-110 transition-[filter]"}>
        <span className="w-2 h-2 rounded-full bg-white animate-pulse" /><Tv className="w-3.5 h-3.5" />Gledaj RTV Cazin uživo
      </button>
      {open && (
        <Dialog open onOpenChange={setOpen}>
          <DialogContent className="max-w-4xl p-3 bg-black border-0" data-testid="rtv-live-dialog">
            <DialogTitle className="text-white text-sm flex items-center gap-2 px-1"><span className="w-2 h-2 rounded-full bg-ccn-red animate-pulse" />RTV Cazin – uživo</DialogTitle>
            <div className="relative w-full aspect-video bg-black rounded overflow-hidden">
              <iframe src={STREAM} title="RTV Cazin uživo" className="absolute inset-0 w-full h-full" allow="autoplay; fullscreen; encrypted-media; picture-in-picture" allowFullScreen data-testid="rtv-live-iframe" />
            </div>
          </DialogContent>
        </Dialog>
      )}
    </>
  );
};
