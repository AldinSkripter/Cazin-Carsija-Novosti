import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { api, errMsg, fmtDate, mediaUrl } from "../../lib/api";
import { PageHead } from "./AdminLayout";
import { Button } from "../../components/ui/button";

export function CommentsAdmin() {
  const [status, setStatus] = useState("pending");
  const [items, setItems] = useState([]);
  const [blocked, setBlocked] = useState([]);
  const load = () => {
    if (status === "blocked") api.get("/admin/blocked").then((r) => setBlocked(r.data));
    else api.get("/admin/comments", { params: { status } }).then((r) => setItems(r.data));
  };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { load(); }, [status]);
  const mod = async (id, action) => {
    const reason = action === "block" ? window.prompt("Razlog blokiranja:") : "";
    if (action === "block" && reason === null) return;
    try { await api.post(`/admin/comments/${id}/moderate`, { action, reason }); toast.success("Sačuvano"); load(); } catch (e) { toast.error(errMsg(e)); }
  };
  return (
    <div data-testid="admin-comments">
      <PageHead title="Komentari" sub="Moderacija – sve odluke se evidentiraju u audit logu" />
      <div className="flex gap-2 mb-4 flex-wrap">
        {[["pending", "Na čekanju"], ["reported", "Prijavljeni"], ["approved", "Odobreni"], ["spam", "Spam"], ["rejected", "Odbijeni"], ["blocked", "Blokirani korisnici"]].map(([k, l]) => (
          <Button key={k} size="sm" variant={status === k ? "default" : "outline"} onClick={() => setStatus(k)} data-testid={`comments-tab-${k}`}>{l}</Button>
        ))}
      </div>
      {status === "blocked" ? blocked.map((b) => (
        <div key={b.id} className="bg-white border rounded-md p-3 mb-2 flex justify-between text-sm"><span><strong>{b.name}</strong> · {b.email} · {b.reason} · {b.blocked_by}</span>
          <Button size="sm" variant="outline" onClick={() => api.delete(`/admin/blocked/${b.id}`).then(load)}>Odblokiraj</Button></div>
      )) : items.map((c) => (
        <div key={c.id} className="bg-white border rounded-md p-4 mb-2" data-testid={`admin-comment-${c.id}`}>
          <p className="text-xs text-slate-500">{fmtDate(c.created_at)} · {c.article_title} {c.reports > 0 && <span className="text-ccn-red font-bold">· {c.reports} prijava</span>}</p>
          <p className="text-sm mt-1"><strong>{c.name}</strong> {c.email && <span className="text-slate-400">({c.email})</span>}</p>
          <p className="mt-1 whitespace-pre-line">{c.content}</p>
          <div className="flex gap-2 mt-3 flex-wrap">
            <Button size="sm" className="bg-emerald-600" onClick={() => mod(c.id, "approved")} data-testid={`comment-approve-${c.id}`}>Odobri</Button>
            <Button size="sm" variant="outline" onClick={() => mod(c.id, "rejected")} data-testid={`comment-reject-${c.id}`}>Odbij</Button>
            <Button size="sm" variant="outline" onClick={() => mod(c.id, "spam")}>Spam</Button>
            <Button size="sm" variant="outline" className="text-ccn-red" onClick={() => mod(c.id, "block")} data-testid={`comment-block-${c.id}`}>Blokiraj korisnika</Button>
            <Button size="sm" variant="ghost" onClick={() => mod(c.id, "delete")}>Obriši</Button>
          </div>
        </div>
      ))}
      {status !== "blocked" && !items.length && <p className="text-slate-500 text-sm">Nema komentara.</p>}
    </div>
  );
}

export function Submissions() {
  const [items, setItems] = useState([]);
  const nav = useNavigate();
  const load = () => api.get("/admin/submissions").then((r) => setItems(r.data));
  useEffect(() => { load(); }, []);
  const setStatus = async (id, status) => { await api.post(`/admin/submissions/${id}/status`, { status }); load(); };
  const toDraft = async (id) => { try { const { data } = await api.post(`/admin/submissions/${id}/to-draft`); toast.success("Kreiran nacrt članka"); nav(`/admin/clanci/${data.id}`); } catch (e) { toast.error(errMsg(e)); } };
  const LBL = { new: "Nova", checking: "U provjeri", used: "Iskorištena", rejected: "Odbijena" };
  return (
    <div data-testid="admin-submissions">
      <PageHead title="Prijavljene vijesti" sub="Prijave čitalaca – ne objavljuju se automatski" />
      {items.map((s) => (
        <div key={s.id} className="bg-white border rounded-md p-4 mb-3" data-testid={`submission-${s.id}`}>
          <div className="flex justify-between gap-3 flex-wrap"><h2 className="font-bold">{s.title}</h2><span className="text-xs bg-ccn-mist px-2 py-1 rounded-full">{LBL[s.status]}</span></div>
          <p className="text-xs text-slate-500 mt-1">{fmtDate(s.created_at)} · {s.name} · {s.contact} · saglasnosti potvrđene</p>
          <p className="mt-2 text-sm whitespace-pre-line">{s.description}</p>
          {s.photos?.length > 0 && <div className="flex gap-2 mt-3">{s.photos.map((p) => <a key={p.id} href={mediaUrl(p.large)} target="_blank" rel="noreferrer"><img src={mediaUrl(p.thumb)} alt="" className="w-24 h-20 object-cover rounded-sm" /></a>)}</div>}
          <div className="flex gap-2 mt-3 flex-wrap">
            <Button size="sm" variant="outline" onClick={() => setStatus(s.id, "checking")} data-testid={`submission-checking-${s.id}`}>U provjeri</Button>
            <Button size="sm" className="bg-ccn-navy" onClick={() => toDraft(s.id)} data-testid={`submission-to-draft-${s.id}`}>Pretvori u nacrt članka</Button>
            <Button size="sm" variant="outline" className="text-ccn-red" onClick={() => setStatus(s.id, "rejected")} data-testid={`submission-reject-${s.id}`}>Odbij</Button>
          </div>
        </div>
      ))}
      {!items.length && <p className="text-slate-500 text-sm">Nema prijava.</p>}
    </div>
  );
}

const CAMP_STATUS = { draft: "Nacrt", sending: "Šalje se…", sent: "Poslano", failed: "Greška" };

function CampaignRow({ c, onSend }) {
  return (
    <div className="text-sm py-2 border-b flex flex-wrap items-center justify-between gap-2" data-testid={`newsletter-campaign-${c.id}`}>
      <div>
        <p className="font-medium">{c.subject} {c.created_by === "Automatski" && <span className="text-xs text-ccn-turquoise">(automatski)</span>}</p>
        <p className="text-xs text-slate-500">{c.article_ids.length} vijesti · {fmtDate(c.created_at)} · <span data-testid={`newsletter-campaign-status-${c.id}`}>{CAMP_STATUS[c.status] || c.status}</span>{c.sent_count != null && ` · poslano ${c.sent_count}/${c.recipients}`}{c.failed_count > 0 && `, neuspjelo ${c.failed_count}`}</p>
      </div>
      {(c.status === "draft" || c.status === "failed") && <Button size="sm" className="bg-ccn-navy" onClick={() => onSend(c)} data-testid={`newsletter-send-${c.id}`}>Pošalji</Button>}
    </div>
  );
}

export function NewsletterAdmin() {
  const [subs, setSubs] = useState([]);
  const [camps, setCamps] = useState([]);
  const load = () => { api.get("/admin/newsletter/subscribers").then((r) => setSubs(r.data)); api.get("/admin/newsletter/campaigns").then((r) => setCamps(r.data)); };
  useEffect(() => { load(); }, []);
  const send = async (c) => {
    if (!window.confirm(`Poslati "${c.subject}" svim potvrđenim pretplatnicima?`)) return;
    try { await api.post(`/admin/newsletter/campaigns/${c.id}/send`); toast.success("Slanje je pokrenuto"); load(); setTimeout(load, 4000); } catch (e) { toast.error(errMsg(e)); }
  };
  const create = async (kind) => { try { await api.post("/admin/newsletter/campaigns", { kind }); toast.success("Kampanja pripremljena"); load(); } catch (e) { toast.error(errMsg(e)); } };
  const exportCsv = () => {
    const rows = [["email", "status", "frequency", "consent_at", "consent_text"], ...subs.map((s) => [s.email, s.status, s.frequency, s.consent_at, s.consent_text])];
    const blob = new Blob([rows.map((r) => r.map((x) => `"${String(x ?? "").replace(/"/g, '""')}"`).join(",")).join("\n")], { type: "text/csv" });
    const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = "pretplatnici.csv"; a.click();
  };
  const confirmed = subs.filter((s) => s.status === "confirmed").length;
  return (
    <div data-testid="admin-newsletter">
      <PageHead title="Newsletter" sub={`${subs.length} prijava · ${confirmed} potvrđenih (double opt-in)`}>
        <Button variant="outline" onClick={exportCsv} data-testid="newsletter-export">Izvoz CSV</Button>
        <Button variant="outline" onClick={() => create("daily")} data-testid="newsletter-create-daily">Dnevni pregled</Button>
        <Button className="bg-ccn-navy" onClick={() => create("weekly")} data-testid="newsletter-create-weekly">Sedmični pregled</Button>
      </PageHead>
      <p className="text-sm bg-amber-50 border border-amber-200 text-amber-900 px-4 py-2 rounded-sm mb-5">Sve ide preko ugrađenog e-mail servisa. Dnevni pregled se automatski šalje svaki dan u 19h, a sedmični nedjeljom u 19h (najčitanije vijesti, svakom pretplatniku prema izabranoj učestalosti). Ručno: napravite pregled i kliknite „Pošalji“. Svaki e-mail ima link za odjavu.</p>
      <div className="grid lg:grid-cols-2 gap-5">
        <div className="bg-white border rounded-md p-4"><h2 className="font-bold mb-3">Kampanje</h2>
          {camps.length === 0 && <p className="text-sm text-slate-500">Još nema kampanja.</p>}
          {camps.map((c) => <CampaignRow key={c.id} c={c} onSend={send} />)}
        </div>
        <div className="bg-white border rounded-md p-4 max-h-[500px] overflow-y-auto"><h2 className="font-bold mb-3">Pretplatnici</h2>
          {subs.map((s) => (
            <p key={s.id} className="text-sm py-1.5 border-b flex justify-between gap-2"><span>{s.email} <span className="text-xs text-slate-400">({s.status}, {s.frequency})</span></span>
              <button className="text-xs text-ccn-red" onClick={() => api.delete(`/admin/newsletter/subscribers/${s.id}`).then(load)}>obriši</button></p>
          ))}
        </div>
      </div>
    </div>
  );
}
