import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "../../lib/api";
import { useSeo } from "../../lib/seo";
import { useSite } from "../../lib/auth";
import { HomeBlock, MostRead } from "../../components/public/HomeBlocks";
import { WeatherWidget } from "../../components/public/WeatherWidget";
import { AdSlot } from "../../components/public/AdSlot";
import { AdsterraBanner } from "../../components/public/AdsterraBanner";
import { NewsletterForm } from "../../components/public/NewsletterForm";
import { Skeleton } from "../../components/ui/skeleton";

const SIDE_AFTER = 5;

export default function Home() {
  const [params] = useSearchParams();
  const preview = params.get("preview") === "1";
  const [blocks, setBlocks] = useState(null);
  const { site } = useSite();
  useSeo({
    siteName: site.site_name, description: site.tagline,
    jsonLd: { "@context": "https://schema.org", "@type": "NewsMediaOrganization", name: site.site_name, url: window.location.origin, logo: window.location.origin + "/icon-512.png" },
  });
  useEffect(() => {
    api.get("/public/home", { params: { preview } }).then((r) => setBlocks(r.data.blocks)).catch(() => setBlocks([]));
  }, [preview]);
  if (!blocks) {
    return <div className="max-w-7xl mx-auto px-4 py-6 grid gap-4"><Skeleton className="h-[420px]" /><Skeleton className="h-40" /></div>;
  }
  const hero = blocks.filter((b) => b.type === "hero");
  const rest = blocks.filter((b) => b.type !== "hero");
  const top = rest.slice(0, SIDE_AFTER);
  const bottom = rest.slice(SIDE_AFTER);
  return (
    <div className="max-w-7xl mx-auto px-4 py-6 md:py-8" data-testid="home-page">
      {preview && <div className="mb-4 bg-ccn-gold text-ccn-navy font-bold text-sm px-4 py-2 rounded-sm" data-testid="home-preview-banner">PREGLED NACRTA POČETNE STRANICE – nije javno objavljeno</div>}
      {hero.map((b) => <HomeBlock key={b.id} b={b} />)}
      <div className="grid lg:grid-cols-12 gap-10 mt-12">
        <div className="lg:col-span-8 space-y-14">{top.map((b) => <HomeBlock key={b.id} b={b} />)}</div>
        <aside className="lg:col-span-4 space-y-6 lg:sticky lg:top-[180px] self-start">
          <MostRead />
          <WeatherWidget />
          <AdSlot position="sidebar" />
          <NewsletterForm />
        </aside>
      </div>
      {!preview && <div className="mt-10"><AdsterraBanner variant="native" /></div>}
      <div className="space-y-14 mt-14">{bottom.map((b) => <HomeBlock key={b.id} b={b} />)}</div>
    </div>
  );
}
