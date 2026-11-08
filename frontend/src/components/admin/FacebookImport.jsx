import { useEffect, useState } from "react";
import { Facebook, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { api, errMsg, fmtDate } from "../../lib/api";
import { Switch } from "../ui/switch";
import { Button } from "../ui/button";
import { Dialog, DialogContent, DialogTitle } from "../ui/dialog";

export const FacebookImport = ({ onDone }) => {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [removeSamples, setRemoveSamples] = useState(false);
  const [res, setRes] = useState(null);
  const [auto, setAuto] = useState(null);
  const [people, setPeople] = useState([]);
  useEffect(() => { if (open) { api.get("/admin/facebook/auto").then((r) => setAuto(r.data)); api.get("/admin/users/directory").then((r) => setPeople(r.data)); } }, [open]);
  const saveAuto = async (body, msg) => {
    try { const r = await api.put("/admin/facebook/auto", body); setAuto(r.data); toast.success(msg); } catch (e) { toast.error(errMsg(e)); }
  };
  const toggleAuto = (v) => saveAuto({ enabled: v }, v ? "Automatski uvoz uključen" : "Automatski uvoz isključen");
  const run = async () => {
    setBusy(true);
    try {
      const r = await api.post("/admin/facebook/import", { limit: 8, remove_samples: removeSamples });
      setRes(r.data);
      if (r.data.imported.length) toast.success(`Uvezeno ${r.data.imported.length} objava`); else toast.info("Nema novih objava za uvoz");
      onDone?.();
    } catch (e) { toast.error(errMsg(e)); } finally { setBusy(false); }
  };
  const close = () => { setOpen(false); setRes(null); };
  return (
    <>
      <Button variant="outline" onClick={() => setOpen(true)} data-testid="fb-import-button"><Facebook className="w-4 h-4 mr-1" />Uvezi sa Facebooka</Button>
      {open && (
        <Dialog open onOpenChange={close}>
          <DialogContent className="max-w-lg" data-testid="fb-import-dialog">
            <DialogTitle>Uvoz objava sa Facebook stranice</DialogTitle>
            {res ? (
              <div className="grid gap-2 text-sm" data-testid="fb-import-result">
                <p>Objavljeno: <strong>{res.imported.length}</strong> · Već uvezeno ranije: {res.skipped}{res.removed_samples > 0 && ` · Obrisano probnih: ${res.removed_samples}`}</p>
                <ul className="list-disc pl-5">{res.imported.map((t) => <li key={t}>{t}</li>)}</ul>
                <Button className="bg-ccn-navy w-fit" onClick={close} data-testid="fb-import-close">Zatvori</Button>
              </div>
            ) : (
              <div className="grid gap-3 text-sm">
                <p>Preuzimaju se najnovije javne objave sa vaše Facebook stranice (tekst, slika, datum) i odmah objavljuju na portalu u rubrici Cazin. Objave koje su već uvezene se preskaču. Facebook javno prikazuje samo zadnjih ~5 objava, pa uvoz pokrećite redovno.</p>
                <label className="flex gap-2 items-center"><input type="checkbox" checked={removeSamples} onChange={(e) => setRemoveSamples(e.target.checked)} data-testid="fb-import-remove-samples" />Obriši probne „primjer“ članke</label>
                <Button className="bg-ccn-navy w-fit" disabled={busy} onClick={run} data-testid="fb-import-run">{busy ? <Loader2 className="w-4 h-4 mr-1 animate-spin" /> : <Facebook className="w-4 h-4 mr-1" />}Uvezi i objavi</Button>
                {auto && (
                  <div className="border-t pt-3 grid gap-1" data-testid="fb-auto-box">
                    <label className="flex gap-2 items-center font-semibold"><Switch checked={auto.enabled} onCheckedChange={toggleAuto} data-testid="fb-auto-switch" />Automatski uvoz svaki sat</label>
                    <p className="text-xs text-slate-500" data-testid="fb-auto-status">Objavljuje samo nove objave, već uvezene nikad ne duplira. Zadnja provjera: {auto.last_run ? `${fmtDate(auto.last_run)} (novih: ${auto.last_imported})` : "još nije pokrenuta"}</p>
                    {auto.last_error && <p className="text-xs text-ccn-red" data-testid="fb-auto-error">Zadnja greška: {auto.last_error}</p>}
                    <label className="grid gap-1 text-xs font-semibold mt-2">Autor uvezenih objava (ručno i automatski)
                      <select value={auto.author_id || ""} onChange={(e) => saveAuto({ author_id: e.target.value }, "Autor sačuvan")} className="border rounded-sm px-3 py-2 text-sm font-normal" data-testid="fb-author-select">
                        <option value="">Vlasnik portala (prvi Super Admin)</option>
                        {people.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
                      </select>
                    </label>
                  </div>
                )}
              </div>
            )}
          </DialogContent>
        </Dialog>
      )}
    </>
  );
};
