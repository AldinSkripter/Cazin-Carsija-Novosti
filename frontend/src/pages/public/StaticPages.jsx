import { useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { api, errMsg } from "../../lib/api";
import { useSeo } from "../../lib/seo";
import { useSite } from "../../lib/auth";
import { CamerasWidget } from "../../components/public/CamerasWidget";
import NotFound from "./NotFound";

export function StaticPage() {
  const { slug } = useParams();
  const { site } = useSite();
  const [p, setP] = useState(null);
  const [err, setErr] = useState(false);
  useEffect(() => { setErr(false); api.get(`/public/pages/${slug}`).then((r) => setP(r.data)).catch(() => setErr(true)); }, [slug]);
  useSeo({ siteName: site.site_name, title: p?.seo_title || p?.title, description: p?.seo_description });
  if (err) return <NotFound />;
  if (!p) return null;
  return (
    <div className="max-w-3xl mx-auto px-4 py-10" data-testid={`static-page-${slug}`}>
      <h1 className="font-serif-news text-3xl sm:text-4xl font-black mb-6">{p.title}</h1>
      <div className="article-body" dangerouslySetInnerHTML={{ __html: p.content }} />
      {slug === "politika-privatnosti" && <PrivacyRequest />}
    </div>
  );
}

function PrivacyRequest() {
  const [f, setF] = useState({ email: "", type: "access", message: "" });
  const submit = async (e) => {
    e.preventDefault();
    try { await api.post("/public/privacy-request", f); toast.success("Zahtjev je zaprimljen"); setF({ email: "", type: "access", message: "" }); }
    catch (err) { toast.error(errMsg(err)); }
  };
  return (
    <form onSubmit={submit} className="mt-10 bg-white border border-ccn-mist rounded-md p-5 grid gap-3" data-testid="privacy-request-form">
      <h2 className="font-bold">Zahtjev za pristup ili brisanje ličnih podataka</h2>
      <input type="email" required placeholder="E-mail" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} className="border rounded-sm px-3 py-2 text-sm" data-testid="privacy-email" />
      <select value={f.type} onChange={(e) => setF({ ...f, type: e.target.value })} className="border rounded-sm px-3 py-2 text-sm" data-testid="privacy-type">
        <option value="access">Pristup podacima</option><option value="delete">Brisanje podataka</option><option value="correction">Ispravka podataka</option>
      </select>
      <textarea rows={3} placeholder="Napomena" value={f.message} onChange={(e) => setF({ ...f, message: e.target.value })} className="border rounded-sm px-3 py-2 text-sm" />
      <button className="justify-self-start bg-ccn-navy text-white px-4 py-2 rounded-sm text-sm" data-testid="privacy-submit">Pošalji zahtjev</button>
    </form>
  );
}

export function AuthorsPage() {
  const { site } = useSite();
  const [list, setList] = useState([]);
  useSeo({ siteName: site.site_name, title: "Autori" });
  useEffect(() => { api.get("/public/authors").then((r) => setList(r.data)).catch(() => {}); }, []);
  return (
    <div className="max-w-5xl mx-auto px-4 py-10" data-testid="authors-page">
      <h1 className="font-serif-news text-3xl sm:text-4xl font-black mb-8">Autori</h1>
      <div className="grid sm:grid-cols-2 md:grid-cols-3 gap-5">
        {list.map((u) => (
          <Link key={u.id} to={`/autor/${u.slug}`} className="bg-white border border-ccn-mist rounded-md p-5 hover:shadow-md transition-shadow" data-testid={`author-${u.slug}`}>
            <div className="w-12 h-12 rounded-full bg-ccn-navy text-ccn-gold font-bold flex items-center justify-center">{u.name?.[0]}</div>
            <p className="font-bold mt-3">{u.name}</p>
            <p className="text-sm text-slate-500 line-clamp-2">{u.bio}</p>
          </Link>
        ))}
      </div>
    </div>
  );
}

export function CamerasPage() {
  const { site } = useSite();
  useSeo({ siteName: site.site_name, title: "Kamere uživo sa graničnih prijelaza", description: "Kamere uživo: GP Maljevac, Izačić i drugi granični prijelazi." });
  return <div className="max-w-7xl mx-auto px-4 py-8" data-testid="cameras-page"><CamerasWidget title="Kamere uživo – granični prijelazi" /></div>;
}

export function NewsletterPage() {
  const [params] = useSearchParams();
  const [msg, setMsg] = useState("Obrada…");
  useEffect(() => {
    const t = params.get("potvrda") || params.get("odjava");
    const ep = params.get("potvrda") ? "confirm" : "unsubscribe";
    if (!t) { setMsg("Nedostaje link."); return; }
    api.get(`/public/newsletter/${ep}`, { params: { token: t } })
      .then(() => setMsg(ep === "confirm" ? "Hvala! Vaša prijava na newsletter je potvrđena." : "Uspješno ste se odjavili s newslettera."))
      .catch((e) => setMsg(errMsg(e)));
  }, [params]);
  return <div className="max-w-xl mx-auto px-4 py-24 text-center" data-testid="newsletter-status"><h1 className="font-serif-news text-2xl font-black">{msg}</h1></div>;
}

export function SubmitNews() {
  const { site } = useSite();
  useSeo({ siteName: site.site_name, title: "Prijavite vijest" });
  const empty = { name: "", contact: "", title: "", description: "", consent_data: false, consent_rights: false, website: "" };
  const [f, setF] = useState(empty);
  const [files, setFiles] = useState([]);
  const [busy, setBusy] = useState(false);
  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    const fd = new FormData();
    Object.entries(f).forEach(([k, v]) => fd.append(k, v));
    [...files].slice(0, 5).forEach((x) => fd.append("photos", x));
    try { await api.post("/public/submit-news", fd); toast.success("Hvala! Vaša prijava je poslana redakciji na provjeru."); setF(empty); setFiles([]); }
    catch (err) { toast.error(errMsg(err)); } finally { setBusy(false); }
  };
  const cls = "border border-slate-300 rounded-sm px-3 py-2 text-sm w-full";
  return (
    <div className="max-w-2xl mx-auto px-4 py-10" data-testid="submit-news-page">
      <h1 className="font-serif-news text-3xl sm:text-4xl font-black">Prijavite vijest</h1>
      <p className="text-slate-600 mt-2">Bili ste svjedok događaja? Pošaljite nam informacije i fotografije. Prijave se ne objavljuju automatski – redakcija ih provjerava.</p>
      <form onSubmit={submit} className="mt-8 grid gap-4 bg-white p-6 rounded-md border border-ccn-mist">
        <div className="grid sm:grid-cols-2 gap-4">
          <input required placeholder="Ime i prezime *" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} className={cls} data-testid="submit-name" />
          <input required placeholder="E-mail ili telefon *" value={f.contact} onChange={(e) => setF({ ...f, contact: e.target.value })} className={cls} data-testid="submit-contact" />
        </div>
        <input required placeholder="Naslov *" value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} className={cls} data-testid="submit-title" />
        <textarea required rows={6} placeholder="Opis događaja (šta, gdje, kada) *" value={f.description} onChange={(e) => setF({ ...f, description: e.target.value })} className={cls} data-testid="submit-description" />
        <input tabIndex={-1} autoComplete="off" className="hidden" value={f.website} onChange={(e) => setF({ ...f, website: e.target.value })} aria-hidden="true" />
        <label className="text-sm">Fotografije (do 5, JPG/PNG/WebP)
          <input type="file" multiple accept="image/jpeg,image/png,image/webp,image/avif" onChange={(e) => setFiles(e.target.files)} className="block mt-1 text-sm" data-testid="submit-photos" />
        </label>
        <label className="flex gap-2 text-sm"><input type="checkbox" checked={f.consent_data} onChange={(e) => setF({ ...f, consent_data: e.target.checked })} data-testid="submit-consent-data" />Saglasan/na sam s obradom ličnih podataka u svrhu provjere prijave.</label>
        <label className="flex gap-2 text-sm"><input type="checkbox" checked={f.consent_rights} onChange={(e) => setF({ ...f, consent_rights: e.target.checked })} data-testid="submit-consent-rights" />Potvrđujem da imam pravo dostaviti ovaj materijal i fotografije.</label>
        <button disabled={busy} className="justify-self-start bg-ccn-gold text-ccn-navy font-bold px-6 py-2.5 rounded-sm disabled:opacity-50" data-testid="submit-news-button">{busy ? "Šaljem…" : "Pošalji prijavu"}</button>
      </form>
    </div>
  );
}
