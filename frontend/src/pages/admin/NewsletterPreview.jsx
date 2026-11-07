import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Monitor, Smartphone, Send, FlaskConical } from "lucide-react";
import { api, errMsg } from "../../lib/api";
import { Dialog, DialogContent, DialogTitle } from "../../components/ui/dialog";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Textarea } from "../../components/ui/textarea";

export function NewsletterPreview({ camp, onClose, onSend, onSaved }) {
  const [html, setHtml] = useState("");
  const [mobile, setMobile] = useState(false);
  const [f, setF] = useState({ subject: "", intro: "" });
  const [busy, setBusy] = useState("");
  const editable = camp && (camp.status === "draft" || camp.status === "failed");

  const loadPreview = (id) => { api.get(`/admin/newsletter/campaigns/${id}/preview`).then((r) => setHtml(r.data.html)).catch((e) => toast.error(errMsg(e))); };
  useEffect(() => {
    if (camp) { setF({ subject: camp.subject, intro: camp.intro || "" }); setHtml(""); loadPreview(camp.id); }
  }, [camp]);

  const save = async () => {
    setBusy("save");
    try { await api.put(`/admin/newsletter/campaigns/${camp.id}`, f); toast.success("Sačuvano"); loadPreview(camp.id); onSaved(); } catch (e) { toast.error(errMsg(e)); }
    setBusy("");
  };
  const test = async () => {
    setBusy("test");
    try { const r = await api.post(`/admin/newsletter/campaigns/${camp.id}/test`); toast.success(`Probni e-mail poslan na ${r.data.email}`); } catch (e) { toast.error(errMsg(e)); }
    setBusy("");
  };

  return (
    <Dialog open={!!camp} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-6xl w-[96vw] p-0 overflow-hidden" data-testid="newsletter-preview-dialog">
        <DialogTitle className="sr-only">Pregled e-maila</DialogTitle>
        {camp && (
          <div className="grid lg:grid-cols-[340px_1fr] max-h-[88vh]">
            <div className="p-5 border-r space-y-4 overflow-y-auto">
              <div><p className="text-xs uppercase tracking-widest text-ccn-turquoise font-bold">Pregled prije slanja</p><h2 className="font-serif text-xl font-bold mt-1">{camp.article_ids.length} vijesti · {camp.recipients} primalaca</h2></div>
              <label className="block text-sm font-medium">Naslov e-maila
                <Input className="mt-1" value={f.subject} disabled={!editable} onChange={(e) => setF({ ...f, subject: e.target.value })} data-testid="newsletter-preview-subject" />
              </label>
              <label className="block text-sm font-medium">Uvodni tekst <span className="text-slate-400 font-normal">(nije obavezno)</span>
                <Textarea className="mt-1" rows={5} value={f.intro} disabled={!editable} placeholder="Npr. Dobro veče! Evo šta se ove sedmice dešavalo u Cazinu…" onChange={(e) => setF({ ...f, intro: e.target.value })} data-testid="newsletter-preview-intro" />
              </label>
              {editable && <Button variant="outline" className="w-full" disabled={busy === "save"} onClick={save} data-testid="newsletter-preview-save">{busy === "save" ? "Čuvam…" : "Sačuvaj i osvježi pregled"}</Button>}
              <div className="border-t pt-4 space-y-2">
                <Button variant="outline" className="w-full" disabled={!!busy} onClick={test} data-testid="newsletter-preview-test"><FlaskConical className="w-4 h-4" />{busy === "test" ? "Šaljem…" : "Pošalji probni na moj e-mail"}</Button>
                {editable && <Button className="w-full bg-ccn-navy" disabled={!!busy} onClick={() => onSend(camp)} data-testid="newsletter-preview-send-all"><Send className="w-4 h-4" />Pošalji svima</Button>}
              </div>
            </div>
            <div className="bg-slate-100 flex flex-col min-h-[60vh]">
              <div className="flex justify-center gap-2 p-3 border-b bg-white">
                <Button size="sm" variant={mobile ? "outline" : "default"} className={mobile ? "" : "bg-ccn-navy"} onClick={() => setMobile(false)} data-testid="newsletter-preview-desktop"><Monitor className="w-4 h-4" />Računar</Button>
                <Button size="sm" variant={mobile ? "default" : "outline"} className={mobile ? "bg-ccn-navy" : ""} onClick={() => setMobile(true)} data-testid="newsletter-preview-mobile"><Smartphone className="w-4 h-4" />Mobitel</Button>
              </div>
              <div className="flex-1 overflow-auto p-4 flex justify-center">
                {html ? <iframe title="Pregled e-maila" srcDoc={html} sandbox="allow-same-origin allow-popups" className="bg-white shadow-lg rounded-md transition-[width] duration-300" style={{ width: mobile ? 380 : 680, height: "72vh", border: 0 }} data-testid="newsletter-preview-frame" /> : <p className="text-sm text-slate-500 self-center">Učitavam pregled…</p>}
              </div>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
