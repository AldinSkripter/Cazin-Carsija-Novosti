import { useState } from "react";
import { toast } from "sonner";
import { api, errMsg } from "../../lib/api";

export function NewsletterForm({ dark = false }) {
  const [email, setEmail] = useState("");
  const [consent, setConsent] = useState(false);
  const [frequency, setFrequency] = useState("weekly");
  const [busy, setBusy] = useState(false);
  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const { data } = await api.post("/public/newsletter/subscribe", { email, consent, frequency });
      toast.success(data.message);
      setEmail("");
    } catch (err) {
      toast.error(errMsg(err));
    } finally {
      setBusy(false);
    }
  };
  return (
    <form onSubmit={submit} className={`rounded-md p-5 ${dark ? "bg-ccn-navy2 text-white" : "bg-white border border-ccn-mist"}`} data-testid="newsletter-form">
      <h2 className="font-bold text-base">Newsletter</h2>
      <p className={`text-sm mt-1 ${dark ? "text-white/60" : "text-slate-500"}`}>Najvažnije vijesti iz Krajine u vašem inboxu.</p>
      <label htmlFor="nl-email" className="sr-only">E-mail</label>
      <input id="nl-email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="vas@email.com" data-testid="newsletter-email"
        className="mt-3 w-full rounded-sm border border-slate-300 px-3 py-2 text-sm text-ccn-navy" />
      <select value={frequency} onChange={(e) => setFrequency(e.target.value)} aria-label="Učestalost" data-testid="newsletter-frequency"
        className="mt-2 w-full rounded-sm border border-slate-300 px-3 py-2 text-sm text-ccn-navy">
        <option value="daily">Dnevni pregled</option>
        <option value="weekly">Sedmični pregled</option>
      </select>
      <label className="flex gap-2 items-start mt-2 text-xs">
        <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} className="mt-0.5" data-testid="newsletter-consent" />
        <span>Saglasan/na sam s primanjem newslettera i politikom privatnosti.</span>
      </label>
      <button disabled={busy || !consent} className="mt-3 w-full bg-ccn-teal text-ccn-navy font-bold rounded-sm py-2 text-sm hover:bg-ccn-gold transition-colors disabled:opacity-50" data-testid="newsletter-submit">
        {busy ? "Šaljem…" : "Prijavi se"}
      </button>
    </form>
  );
}
