import { Share2, Link2, Copy, ShieldCheck } from "lucide-react";
import { SiFacebook, SiWhatsapp, SiViber, SiTelegram, SiX } from "react-icons/si";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { shareUrl } from "../../lib/api";

const copy = (text, msg) => {
  navigator.clipboard?.writeText(text).then(() => toast.success(msg)).catch(() => toast.error("Kopiranje nije uspjelo"));
};

export function Share({ a, size = "md" }) {
  const url = shareUrl(a);
  const u = encodeURIComponent(url);
  const t = encodeURIComponent(a.title);
  const links = [
    ["facebook", "Facebook", SiFacebook, "#1877F2", `https://www.facebook.com/sharer/sharer.php?u=${u}`],
    ["whatsapp", "WhatsApp", SiWhatsapp, "#25D366", `https://wa.me/?text=${t}%20${u}`],
    ["viber", "Viber", SiViber, "#7360F2", `viber://forward?text=${t}%20${u}`],
    ["telegram", "Telegram", SiTelegram, "#229ED9", `https://t.me/share/url?url=${u}&text=${t}`],
    ["x", "X (Twitter)", SiX, "#111111", `https://twitter.com/intent/tweet?url=${u}&text=${t}`],
  ];
  const s = size === "lg" ? "w-11 h-11" : "w-9 h-9";
  const native = typeof navigator !== "undefined" && navigator.share;
  return (
    <div className="flex flex-wrap gap-2" data-testid={`share-buttons-${size}`}>
      {links.map(([k, label, I, color, href]) => (
        <a key={k} href={href} target="_blank" rel="noopener noreferrer" aria-label={`Podijeli na ${label}`} title={`Podijeli na ${label}`}
          data-testid={`share-${k}-${size}`} style={{ backgroundColor: color }}
          className={`${s} rounded-full text-white flex items-center justify-center ring-1 ring-white/20 hover:-translate-y-0.5 hover:shadow-lg transition-transform`}>
          <I className="w-4 h-4" />
        </a>
      ))}
      {native && (
        <button onClick={() => navigator.share({ title: a.title, url }).catch(() => {})} aria-label="Podijeli" title="Podijeli" data-testid={`share-native-${size}`}
          className={`${s} rounded-full bg-ccn-teal text-ccn-navy flex items-center justify-center hover:-translate-y-0.5 transition-transform`}><Share2 className="w-4 h-4" /></button>
      )}
      <button onClick={() => copy(url, "Link kopiran")} aria-label="Kopiraj link" title="Kopiraj link" data-testid={`share-copy-${size}`}
        className={`${s} rounded-full bg-ccn-mist text-ccn-navy flex items-center justify-center hover:bg-ccn-gold transition-colors`}><Link2 className="w-4 h-4" /></button>
    </div>
  );
}

export function ShareBottom({ a }) {
  return (
    <div className="mt-10 rounded-xl border border-ccn-mist p-5 flex flex-wrap items-center justify-between gap-4" data-testid="share-bottom">
      <p className="font-serif-news font-bold text-lg">Podijelite ovu vijest</p>
      <Share a={a} size="lg" />
    </div>
  );
}

export function ReuseBox({ a }) {
  const url = shareUrl(a);
  const names = (a.authors || []).map((u) => u.name).join(", ") || "Redakcija CČN";
  const plain = `Izvor: Cazin Čaršija Novosti (CČN), autor: ${names}. Cijeli tekst: ${url}`;
  const html = `<p>Izvor: <a href="${url}">Cazin Čaršija Novosti (CČN)</a>, autor: ${names}</p>`;
  return (
    <aside className="mt-6 rounded-xl bg-ccn-navy text-white p-5 sm:p-6" data-testid="reuse-box">
      <p className="flex items-center gap-2 font-bold text-ccn-gold"><ShieldCheck className="w-5 h-5" />Preuzimanje dozvoljeno uz ime autora i link</p>
      <p className="text-sm text-white/75 mt-2">Ovaj tekst smijete prenijeti samo uz navođenje autora i aktivan link na izvorni članak. <Link to="/stranica/uslovi-koristenja" className="underline hover:text-ccn-teal">Uslovi korištenja</Link></p>
      <p className="mt-4 text-sm bg-white/10 rounded-md px-4 py-3 font-mono break-words [overflow-wrap:anywhere]" data-testid="reuse-text">{plain}</p>
      <div className="flex flex-wrap gap-2 mt-4">
        <button onClick={() => copy(plain, "Tekst za preuzimanje kopiran")} data-testid="reuse-copy-text"
          className="inline-flex items-center gap-2 bg-ccn-teal text-ccn-navy font-semibold text-sm px-4 py-2 rounded-full hover:opacity-90 transition-opacity"><Copy className="w-4 h-4" />Kopiraj tekst</button>
        <button onClick={() => copy(html, "HTML kod kopiran")} data-testid="reuse-copy-html"
          className="inline-flex items-center gap-2 border border-white/30 text-white text-sm px-4 py-2 rounded-full hover:bg-white/10 transition-colors"><Copy className="w-4 h-4" />Kopiraj HTML za web stranice</button>
      </div>
    </aside>
  );
}
