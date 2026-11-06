import { Link } from "react-router-dom";
import { useSeo } from "../../lib/seo";

export default function NotFound() {
  useSeo({ title: "Stranica nije pronađena", noindex: true });
  return (
    <div className="max-w-xl mx-auto px-4 py-24 text-center" data-testid="not-found-page">
      <p className="font-serif-news text-8xl font-black text-ccn-gold">404</p>
      <h1 className="font-serif-news text-2xl font-black mt-4">Stranica nije pronađena</h1>
      <p className="text-slate-600 mt-2">Vijest ili stranica koju tražite ne postoji ili je premještena.</p>
      <div className="flex gap-3 justify-center mt-8">
        <Link to="/" className="bg-ccn-navy text-white px-5 py-2 rounded-sm font-semibold" data-testid="not-found-home">Naslovna</Link>
        <Link to="/pretraga" className="border border-ccn-navy px-5 py-2 rounded-sm font-semibold">Pretraga</Link>
      </div>
    </div>
  );
}
